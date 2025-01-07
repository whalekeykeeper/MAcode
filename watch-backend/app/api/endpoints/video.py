# /app/api/endpoints/video.py

import itertools
import time
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Union

import networkx as nx
import numpy as np
import spacy
from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api import deps
from app.core.bilingual_subtitle_creator import create_bilingual_vtt
from app.core.logger import logger
from app.core.subtitle_processor import SubtitleProcessor
from app.core.video_subtitles_downloader import download_video_and_subtitles, get_ytb_id
from app.models import Families, Graph, User, Video, Vocabulary, Word
from app.schemas.requests import VideoRequest
from app.schemas.responses import VideoResponse

router = APIRouter()

NLP_EN = spacy.load("en_core_web_lg")
NLP_ZH = spacy.load("zh_core_web_lg")
VALID_POS = ["NOUN", "VERB", "ADJ", "ADV", "PROPN", "INTJ"]


@router.post("/", response_model=VideoResponse, status_code=201)
async def download_and_process_video_and_subtitles(
        new_video: VideoRequest,
        session: AsyncSession = Depends(deps.get_session),
        current_user: User = Depends(deps.get_current_user),
        x_user_uuid: Optional[str] = Header(None)
):
    """Process video request with proper transaction management."""
    logger.debug(f"Request received")
    logger.debug(f"Headers: {x_user_uuid}")
    logger.debug(f"Request body: {new_video}")
    start_time = time.time()  # Record start time

    try:

        url = new_video.video_url
        ytb_id = get_ytb_id(url)
        static_folder = Path(__file__).parent.parent.parent.parent / "static"

        # Check if ytb_id already in the database.
        existing_video = await _get_existing_video(ytb_id, session)

        if existing_video:  # If video already exists in the database
            logger.info(f"Video {ytb_id} already exists in the database.")
            await _ensure_bilingual_subtitles(existing_video, static_folder, session)
            if await current_user_has_watched(current_user.id, existing_video.id, session):
                # If the user has already watched the video, do nothing, just return the video.
                logger.info(f"User {current_user.id} has already watched video {existing_video.id}.")
                return existing_video
            # If the user hasn't watched the video, process the video for the user.
            await _process_existed_video_for_new_user(current_user, existing_video.id, session)
            logger.info(f"Start to process existed video {ytb_id} for user {current_user.id}.")
            await session.commit()
            return existing_video

        else:
            logger.info(f"Video {ytb_id} does not exist in the database. Start to process its subtitle.")
            new_video = await _process_new_video(url, ytb_id, static_folder, current_user, session)
            await session.commit()
            return new_video

    except Exception as e:
        logger.error(f"Transaction failed: {str(e)}")
        await session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to process video request: {str(e)}")
    finally:
        end_time = time.time()  # Record end time
        elapsed_time = end_time - start_time
        logger.info(f"Elapsed time: {elapsed_time:.2f} seconds")


async def _get_existing_video(ytb_id: str, session: AsyncSession) -> Optional[Video]:
    """Get video if it exists in database."""
    stmt = select(Video).where(Video.ytb_id == ytb_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def _ensure_bilingual_subtitles(
        video: Video, static_folder: Path, session: AsyncSession
):
    """Ensure bilingual subtitles exist for the video."""
    bilingual_vtt_path = static_folder / video.ytb_id / f"{video.ytb_id}_bilingual.vtt"
    if not bilingual_vtt_path.exists():
        video.vtt_path = create_bilingual_vtt(video.ytb_id, static_folder)
        session.add(video)
        logger.info(
            f"Bilingual subtitles created for video {video.ytb_id}. Check why the bilingual subtitle is not created."
        )


async def current_user_has_watched(
        user_id: int, video_id: int, session: AsyncSession
) -> bool:
    """Check if the given user has already watched the video using User table."""
    stmt = select(User.video_ids).where(User.id == user_id)
    user_video_ids = (await session.execute(stmt)).scalar_one_or_none()

    return video_id in user_video_ids if user_video_ids else False


async def _process_existed_video_for_new_user(
        user: User, video_id: int, session: AsyncSession
):
    """Process existed video for user who hasn't watched it before."""

    # Fetch video_word_ids from Video
    stmt = select(Video.word_ids).where(Video.id == video_id)
    video_word_ids = (await session.execute(stmt)).scalar_one_or_none()

    if video_word_ids:
        await process_user_specific_data(session, user, video_id, video_word_ids)

    else:
        logger.error(f"word_list of video {new_video.id} not found for user {user.id}")
        raise HTTPException(status_code=404, detail=f"word_list of video {new_video.id} not found for user {user.id}")

    logger.info(f"Updated user {user.id} with video {video_id} and associated words.")


async def _process_new_video(
        url: str,
        ytb_id: str,
        static_folder: Path,
        user: User,
        session: AsyncSession
) -> Video:
    """Download and process new video."""
    try:
        from pathlib import Path
        # Download video and create subtitles
        download_video_and_subtitles(ytb_id, url, static_folder)
        bilingual_vtt_path = create_bilingual_vtt(ytb_id, static_folder)

        logger.debug(f"Video {ytb_id} downloaded and bilingual subtitles created.")
        logger.debug(f"Start to process new video {ytb_id} for user {user.id}.")
        # Create video entry, mainly for generating id.
        new_video = Video(
            url=url,
            ytb_id=ytb_id,
            video_path=f"{static_folder}/{ytb_id}/{ytb_id}.mp4",
            vtt_path=str(bilingual_vtt_path),
        )
        session.add(new_video)
        await session.flush()

        logger.debug(f"Video {ytb_id} created in the database.")
        # Process subtitles for all tables for new videos
        subtitle_processor = SubtitleProcessor()
        await subtitle_processor.process_subtitles(
            ytb_id=new_video.ytb_id,
            user_uuid=user.uuid,
            valid_pos=VALID_POS,
            session=session
        )

        stmt = select(Video.word_ids).where(Video.id == new_video.id)
        video_word_ids = (await session.execute(stmt)).scalar_one_or_none()
        logger.debug(f"Video {ytb_id} processed for user {user.id}.")
        if video_word_ids:
            logger.info(f"-----Start to process user-specific data for user {user.id}.")
            await process_user_specific_data(session, user, new_video.id, video_word_ids)
        else:
            logger.error(f"word_list of video {new_video.id} not found for user {user.id}")
            raise HTTPException(
                status_code=404,
                detail=f"word_list of video {new_video.id} not found for user {user.id}"
            )

        return new_video

    except Exception as e:
        logger.error(f"Error processing new video: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process new video: {str(e)}"
        )


async def process_user_specific_data(session: AsyncSession, user: User, video_id: int,
                                     video_word_ids: List[int]) -> None:
    logger.info(f"------Processing vocabulary, family, graph for user {user.id}...")
    user.video_ids = list(set(user.video_ids + [video_id]))
    user.word_ids = list(set(user.word_ids + video_word_ids))
    session.add(user)
    await session.flush()
    new_words = await initiate_or_update_vocabulary(session, user, video_word_ids)

    # Check if user has entries in Families table, if not, initiate it, else update it
    stmt = select(Families).where(Families.user_id == user.id)
    families = (await session.execute(stmt)).scalars().all()
    if families:
        await _update_family_with_new_words(user.id, new_words, session)
    else:
        await _initiate_families(user.id, session)

    # Check if user has entries in Graph table, if not, initiate it, else update it
    stmt = select(Graph).where(Graph.user_id == user.id)
    graph = (await session.execute(stmt)).scalar_one_or_none()
    if graph:
        await _update_graph(user.id, session)
    else:
        # Update Graph table
        await _initiate_graph(user.id, session)

    logger.info(f"Processed vocabulary, family, graph for user {user.id}.")


async def initiate_or_update_vocabulary(session: AsyncSession, user: User, video_word_ids: List[int]) \
        -> Dict[str, List[List[Union[int, str]]]]:
    logger.info(f"------Initiating or updating vocabulary for user {user.id}...")
    # Check if current user has Vocabulary, if not, initiate it, else update it
    stmt = select(Vocabulary).where(Vocabulary.user_id == user.id)
    vocabulary = (await session.execute(stmt)).scalar_one_or_none()
    new_words = {}  # Collect new words added to the vocabulary

    logger.info(f"------Start to update vocabulary for user {user.id}...")
    if vocabulary:
        vocabulary_dict = vocabulary.vocabulary
        for word_id in video_word_ids:
            stmt = select(Word).where(Word.id == word_id)
            word = (await session.execute(stmt)).scalar_one_or_none()
            if word and word.language == "en" and not NLP_EN.vocab[str(word.lemma)].is_stop and word.lemma in VALID_POS:
                key = f"{word.lemma};{word.pos}"
                if key not in vocabulary_dict:
                    vocabulary_dict[key] = []
                    new_words[lemma] = []
                vocabulary_dict[key].append([word.id, word.lemma])
                new_words[key].append([word.id, word.lemma])
                await detect_lemma_pos_pair_with_multiple_occrrences(vocabulary_dict)
        session.add(vocabulary)
        await session.flush()
        logger.info(f"-----Vocabulary for user {user.id} updated with new words.")

    else:
        logger.info(f"Vocabulary not found for user {user.id}. Initiating vocabulary.")
        vocabulary_dict = await _initiate_vocabulary(user.id, session)
        await detect_lemma_pos_pair_with_multiple_occrrences(vocabulary_dict)
        new_words = vocabulary_dict
        logger.info(f"Vocabulary for user {user.id} initiated.")

    return new_words


async def detect_lemma_pos_pair_with_multiple_occrrences(vocabulary_dict):
    # If any value in words has more than 5 words, logger it
    lemma_pos_pairs_has_more_than_5_occurrences = 0
    for key, value in vocabulary_dict.items():
        if len(value) > 5:
            logger.info(f"Family {key} has {len(value)} words.")
            lemma_pos_pairs_has_more_than_5_occurrences += 1


async def _initiate_vocabulary(user_id: int, session: AsyncSession) -> Dict[str, List[List[Union[int, str]]]]:
    """
    If the user has no vocabulary, create one.
    The vocabulary is a dictionary with lemma+pos as key, a list of (id, lemma) as value.
    Args:
        user_id: User id
        session: AsyncSession
    """
    # Select all “en” words for the user for later learning purpose
    stmt = select(User).where(User.id == user_id)
    user = (await session.execute(stmt)).scalar_one()

    # Using word_ids to retrieve all words
    stmt = select(Word).where(Word.id.in_(user.word_ids))
    words = (await session.execute(stmt)).scalars().all()

    # Filter words: remove stop words and keep only certain POS
    filtered_words = [
        word for word in words
        if ((word.language == "en" and not NLP_EN.vocab[word.lemma].is_stop
             and word.pos in VALID_POS))
    ]

    # Create dictionary with lemma+pos as key, a list of (id, lemma) as value
    vocabulary_dict: Dict[str, List[List[Union[int, str]]]] = {}
    for word in filtered_words:
        key = f"{word.lemma};{word.pos}"
        if key not in vocabulary_dict:
            vocabulary_dict[key] = []
        vocabulary_dict[key].append([word.id, word.lemma])

    # Create vocabulary entry and update User table
    vocabulary_entry = Vocabulary(
        user_id=user_id,
        vocabulary=vocabulary_dict
    )
    session.add(vocabulary_entry)
    await session.flush()

    # Update User table
    user.vocabulary_id = vocabulary_entry.id
    session.add(user)
    await session.flush()
    await session.commit()

    return vocabulary_dict


async def _initiate_families(user_id: int, session: AsyncSession) -> None:
    logger.info(f"Initiating families for user {user_id}...")
    """Initialize families for a user based on their vocabulary."""
    vocabulary_dict = (
        await session.execute(select(Vocabulary).where(Vocabulary.user_id == user_id))).scalar_one().vocabulary

    families = {}
    for ele in vocabulary_dict.values():
        for id_lemma_list in ele:  # id_lemma_list = [word_id, word_lemma]
            word_id = id_lemma_list[0]
            word_lemma = id_lemma_list[1]
            if word_lemma not in families:
                families[word_lemma] = []
            families[word_lemma].append(word_id)

    # Insert into Families table
    for key, value in families.items():
        family_entry = Families(
            user_id=user_id,
            lemma=key,
            word_ids=value,
        )
        session.add(family_entry)

    # Commit families to the database
    await session.flush()
    await session.commit()
    logger.info(f"Families for user {user_id} initiated.")


async def _update_family_with_new_words(
        user_id: int,
        new_words: Dict[str, List[List[Union[int, str]]]],
        session: AsyncSession) -> None:
    logger.info(f"Updating Families for user {user_id} with new words.")
    """Update Families table with only new words."""

    # Fetch existing families for the user
    stmt = select(Families).where(Families.user_id == user_id)
    existing_families = {
        family.lemma: family for family in (await session.execute(stmt)).scalars().all()
    }

    # Update or create families with new words
    for lemma, words in new_words.items():
        if lemma in existing_families:
            # Family exists; update word_ids
            family = existing_families[lemma]
            existing_word_ids = set(family.word_ids)
            for word in words:
                if word[0] not in existing_word_ids:  # word[0] is the word_id
                    family.word_ids.append(word[0])
            session.add(family)
        else:
            # Create a new family
            new_family = Families(
                user_id=user_id,
                lemma=lemma,
                word_ids=[word[0] for word in words],
            )
            session.add(new_family)

    # Commit the changes
    await session.flush()
    await session.commit()
    logger.info(f"Families for user {user_id} updated with new words.")


async def _initiate_graph(user_id: int, session: AsyncSession,
                          similarity_threshold: float = 0.3) -> None:
    """
    Build a graph connecting families based on vector similarity.
    similarity_threshold has a default value of 0.30.
    If don't want to use this minimal similarity threshold, use  0.0.
    Args:
        user_id: The ID of the current user.
        session: The database session.
        similarity_threshold: Minimum similarity to create an edge.

    Returns:
        None: The graph is stored in the database.
    """
    # Retrieve all families for the user
    logger.info(f"-----Building graph for user {user_id} with similarity_threshold {similarity_threshold}...")
    stmt = select(Families).where(Families.user_id == user_id)
    families = (await session.execute(stmt)).scalars().all()

    if not families:
        logger.info(f"No families found for user {user_id}.")
        return

    # List of vectors, either with all the words' vectors and a mapping,
    # or with the mean vector of each family members
    vectors = []
    # A list to collect vectors for each family
    vectors_list = []
    # Flatten vectors and map them to families
    relation = defaultdict(list)
    if similarity_threshold != 0.0:
        for family in families:
            for word_id in family.word_ids:
                result = await session.execute(select(Word).where(Word.id == word_id))
                word = result.scalar_one()
                if word.vector is not None:
                    relation[family.lemma].append(len(vectors_list))
                    vectors_list.append(word.vector)
                else:
                    # The following warning should never appear since we have already filtered out words without
                    # vectors when initiating/updating the vocabulary
                    logger.warning(f"Word {word.lemma} has no vector.")
        vectors = np.array(vectors_list)
    else:
        for family in families:
            for word_id in family.word_ids:
                result = await session.execute(select(Word).where(Word.id == word_id))
                word = result.scalar_one()
                if word.vector is not None:
                    vectors_list.append(word.vector)
                else:
                    logger.info(f"Word {word.lemma} has no vector.")
            # Compute the mean of the word vectors for the family
            if vectors_list:
                vectors.append(np.mean(vectors_list, axis=0))
            else:
                # The following warning should never appear
                logger.warning(f"Family {family.lemma} has no valid word vectors and will be skipped.")
    if not vectors:
        logger.error("No valid vectors found for any family. Please check.")
        return
    
    # Normalize vectors and compute similarity matrix
    norms = np.linalg.norm(vectors, axis=1)
    if np.any(norms == 0):
        logger.error("Encountered zero norm vector during normalization.")
        return

    normalized_vectors = vectors / norms[:, np.newaxis]
    similarity_matrix = np.dot(normalized_vectors, normalized_vectors.T)

    # Build adjacency list with degree restriction (max 5 edges per family)
    weighted_adj_list = []
    degree = defaultdict(int)  # Track the degree of each node

    if similarity_threshold == 0.0:
        family_names = [family.lemma for family in families]
        relatives = {}

        for i, f1 in enumerate(family_names):
            buffer = []
            for f2 in family_names[i + 1:]:
                pairs = list(itertools.product(relation[f1], relation[f2]))
                for x, y in pairs:
                    if x >= len(similarity_matrix) or y >= len(similarity_matrix):
                        logger.warning(f"Skipping out-of-bounds index: x={x}, y={y}")
                        continue
                score = max(similarity_matrix[x][y] for x, y in pairs)
                if score > 0.3:
                    buffer.append((f1, f2, min(1.0, score)))
            relatives[f1] = sorted(buffer, key=lambda x: -x[2])

        # Restrict edges to max degree of 5
        for f, edges in relatives.items():
            for e in edges:
                if degree[e[0]] < 5 and degree[e[1]] < 5:
                    weighted_adj_list.append(e)
                    degree[e[0]] += 1
                    degree[e[1]] += 1
                else:
                    break
    else:
        families_list = [family.lemma for family in families]
        num_families = len(families_list)
        for i, f1 in enumerate(families_list):
            buffer = []
            for offset, f2 in enumerate(families_list[i + 1:]):
                logger.debug(f"Processing similarity_matrix[{i}][{offset}]")
                j = i + offset + 1  # Adjust index offset

                if j >= num_families:
                    logger.error(f"Index out of bounds: j={j}, num_families={num_families}")
                    continue
                if similarity_matrix[i][j] > similarity_threshold:
                    buffer.append((f1, f2, similarity_matrix[i][j]))
            buffer = sorted(buffer, key=lambda x: -x[2])  # Sort edges by weight

            # Add edges with degree restriction
            for edge in buffer:
                if degree[edge[0]] < 5 and degree[edge[1]] < 5:
                    weighted_adj_list.append(edge)
                    degree[edge[0]] += 1
                    degree[edge[1]] += 1
                else:
                    break

    # Build the graph using networkx
    graph = nx.Graph()
    graph.add_nodes_from([family.lemma for family in families])
    graph.add_weighted_edges_from(weighted_adj_list)
    nx.set_node_attributes(graph, 0.5, "mastery")

    # Convert the graph to a serializable format
    graph_data = nx.node_link_data(graph)

    # Save the graph in the database
    graph_entry = Graph(user_id=user_id)
    session.add(graph_entry)
    await session.flush()
    await session.commit()

    logger.info(f"Graph for user {user_id} built and stored in the database.")


async def _update_graph(user_id: int, session: AsyncSession) -> None:
    # To be implemented
    pass


@router.get("/stream/{video_id}")
async def stream_video(
        video_id: str,
        session: AsyncSession = Depends(deps.get_session),
        current_user: User = Depends(deps.get_current_user),
):
    """Streams the video.
    video_id is the id in Video table, not the ytb_id."""
    # Get video path
    stmt = select(Video).where(Video.id == video_id)
    video = (await session.execute(stmt)).scalar_one_or_none()

    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    if not Path(video.video_path).exists():
        raise HTTPException(status_code=404, detail="Video file not found")

    return FileResponse(video.video_path)


@router.get("/vtt/{video_id}")
async def get_subtitles(
        video_id: str,
        session: AsyncSession = Depends(deps.get_session),
        current_user: User = Depends(deps.get_current_user),
):
    """Streams the subtitle file if user has access. video_id is the id in Video table."""
    # Get VTT path
    stmt = select(Video).where(Video.id == video_id)
    video = (await session.execute(stmt)).scalar_one_or_none()

    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    if not Path(video.vtt_path).exists():
        raise HTTPException(status_code=404, detail="VTT file not found")

    return FileResponse(video.vtt_path, filename=video.vtt_path[-18:])


@router.get("/test")
async def test_endpoint():
    return {"message": "Video endpoint is working"}
