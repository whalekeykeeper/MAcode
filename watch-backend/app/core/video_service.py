import itertools
from collections import defaultdict
from pathlib import Path
from typing import Optional, List, Dict, Union

import numpy as np
from fastapi import HTTPException
from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from tqdm import tqdm

from app.core.logger import logger
from app.core.utils.bilingual_subtitle_creator import create_bilingual_vtt
from app.core.utils.nlp import get_nlp_en, get_nlp_zh
from app.core.utils.subtitle_processor import SubtitleProcessor
from app.core.utils.video_subtitles_downloader import download_video_and_subtitles
from app.models import Video, User, Families, Graph, Vocabulary, Word, GraphNode, GraphEdge

# Load language models
NLP_EN = get_nlp_en()
NLP_ZH = get_nlp_zh()
VALID_POS = ["NOUN", "VERB", "ADJ", "ADV", "PROPN", "INTJ"]


async def get_existing_video(ytb_id: str, session: AsyncSession) -> Optional[Video]:
    """
    Check if a video already exists in the database.

    Args:
        ytb_id: YouTube video ID
        session: Database session

    Returns:
        Video object if found, None otherwise
    """
    stmt = select(Video).where(Video.ytb_id == ytb_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def ensure_bilingual_subtitles(
        video: Video, static_folder: Path, session: AsyncSession
):
    """
    Ensure bilingual subtitles exist for the video.
    If not, create them and update the video record.

    Args:
        video: Video object from database
        static_folder: Path to static files
        session: Database session
    """
    bilingual_vtt_path = static_folder / video.ytb_id / f"{video.ytb_id}_bilingual.vtt"
    if not bilingual_vtt_path.exists():
        video.vtt_path = create_bilingual_vtt(video.ytb_id, static_folder)
        session.add(video)
        logger.info(f"Bilingual subtitles created for video {video.ytb_id}.")


async def current_user_has_watched(
        user_id: int, video_id: int, session: AsyncSession
) -> bool:
    """
    Check if a user has already watched a specific video.

    Args:
        user_id: ID of the user
        video_id: ID of the video
        session: Database session

    Returns:
        bool: True if user has watched the video, False otherwise
    """
    stmt = select(User.video_ids).where(User.id == user_id)
    user_video_ids = (await session.execute(stmt)).scalar_one_or_none()

    return video_id in user_video_ids if user_video_ids else False


async def process_existed_video_for_new_user(
        user: User, video_id: int, session: AsyncSession
):
    """
    Process an existing video for a user who hasn't watched it before.

    This function:
    1. Gets video word IDs
    2. Updates user's vocabulary and graph representation in database
    3. Updates user's video history

    Args:
        user: User object
        video_id: ID of the video to process
        session: Database session
    """
    stmt = select(Video.word_ids).where(Video.id == video_id)
    video_word_ids = (await session.execute(stmt)).scalar_one_or_none()

    if video_word_ids:
        await process_user_specific_data(session, user, video_id, video_word_ids)
    else:
        logger.error(f"word_list of video {video_id} not found for user {user.id}")
        raise HTTPException(status_code=404, detail=f"word_list of video {video_id} not found for user {user.id}")

    logger.info(f"Updated user {user.id} with video {video_id} and associated words.")


async def process_new_video(
        url: str,
        ytb_id: str,
        static_folder: Path,
        user: User,
        session: AsyncSession
) -> Video:
    """Download and process new video."""
    try:
        download_video_and_subtitles(ytb_id, url, static_folder)
        bilingual_vtt_path = create_bilingual_vtt(ytb_id, static_folder)

        logger.debug(f"Video {ytb_id} downloaded and bilingual subtitles created.")
        new_video = Video(
            url=url,
            ytb_id=ytb_id,
            video_path=f"{static_folder}/{ytb_id}/{ytb_id}.mp4",
            vtt_path=str(bilingual_vtt_path),
        )
        session.add(new_video)
        await session.flush()

        subtitle_processor = SubtitleProcessor()
        await subtitle_processor.process_subtitles(
            ytb_id=new_video.ytb_id,
            user_uuid=user.uuid,
            session=session
        )

        stmt = select(Video.word_ids).where(Video.id == new_video.id)
        video_word_ids = (await session.execute(stmt)).scalar_one_or_none()
        if video_word_ids:
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


async def process_user_specific_data(
        session: AsyncSession,
        user: User,
        video_id: int,
        video_word_ids: List[int]
) -> None:
    """
    Process user-specific data after watching a video.

    This function updates:
    1. User's video and word history
    2. User's vocabulary
    3. Word families
    4. Graph as the domain model of the learning process

    Args:
        session: Database session
        user: User object
        video_id: ID of the processed video
        video_word_ids: List of word IDs from the video
    """
    logger.info(f"Processing vocabulary, family, graph for user {user.id}...")
    user.video_ids = list(set(user.video_ids + [video_id]))
    user.word_ids = list(set(user.word_ids + video_word_ids))
    session.add(user)
    await session.flush()

    logger.info(f"Vocabulary initiated or updated for user {user.id}.")

    new_words = await initiate_or_update_vocabulary(session, user, video_word_ids)
    new_word_count = sum(len(word_list) for word_list in new_words.values())

    stmt = select(Families).where(Families.user_id == user.id)
    families = (await session.execute(stmt)).scalars().all()
    if families:
        await update_family_with_new_words(user.id, new_words, session)
    else:
        await initiate_families(user.id, session)
    logger.info(f"Families initiated or updated for user {user.id}.")

    stmt = select(Families).where(Families.user_id == user.id)
    updated_families = (await session.execute(stmt)).scalars().all()
    family_count = len(updated_families)

    stmt = select(Graph).where(Graph.user_id == user.id)
    graph = (await session.execute(stmt)).scalar_one_or_none()
    if graph:
        await update_graph(user.id, session)
    else:
        await initiate_graph(user.id, session)

    graph_nodes = []
    if graph:
        stmt = select(GraphNode).where(GraphNode.graph_id == graph.id)
        graph_nodes = (await session.execute(stmt)).scalars().all()
        node_count = len(graph_nodes)

        # stmt = select(GraphNode).where(GraphNode.graph_id == graph.id if graph else 0)
        # graph_nodes = (await session.execute(stmt)).scalars().all()

        logger.info(f"   [SUMMARY] Processed video {video_id} for user {user.id}:")
        logger.info(f"   ➔ New words added: {new_word_count}")
        logger.info(f"   ➔ Total families: {family_count}")
        logger.info(f"   ➔ Total graph nodes: {node_count}")
        logger.info(f"   ➔ Total videos processed so far: {len(user.video_ids)}")


async def initiate_or_update_vocabulary(session: AsyncSession, user: User, video_word_ids: List[int]) \
        -> Dict[str, List[List[Union[int, str]]]]:
    logger.info(f"Initiating or updating vocabulary for user {user.id}...")
    stmt = select(Vocabulary).where(Vocabulary.user_id == user.id)
    vocabulary = (await session.execute(stmt)).scalar_one_or_none()
    new_words = {}

    if vocabulary:
        vocabulary_dict = vocabulary.vocabulary
        for word_id in video_word_ids:
            stmt = select(Word).where(Word.id == word_id)
            word = (await session.execute(stmt)).scalar_one_or_none()

            # Only add English words to the vocabulary for now
            if word and str(word.language) == "en":
                # For safety
                assert (word.cefr not in ["A1", "A2",
                                          "B1"]), f"[CEFR Error] Word {word.lemma} ({word.pos}) with CEFR {word.cefr} should not exist."

                key = f"{word.lemma};{word.pos}"
                if key not in vocabulary_dict:
                    vocabulary_dict[key] = []
                if key not in new_words:
                    new_words[key] = []

                vocabulary_dict[key].append([word.id, word.lemma])
                # Thos new_words is a dictionary with lemma+pos as key, a list of (id, lemma) as value,
                # and it conveys all the new words in the new video, no matter if this word has already been in the
                # vocabulary. By doing so, we make sure that we collect all the different contexts of the same word.
                new_words[key].append([word.id, word.lemma])

        # # The following detection is just for a general statistics reason
        # await detect_lemma_pos_pair_with_multiple_occurrences(vocabulary_dict)

        await session.flush()
        logger.info(f"Vocabulary for user {user.id} updated with new words.")

    else:
        vocabulary_dict = await initiate_vocabulary(user.id, session)

        # # The following detection is just for a general statistics reason
        # await detect_lemma_pos_pair_with_multiple_occurrences(vocabulary_dict)

        new_words = vocabulary_dict
        logger.info(f"Vocabulary for user {user.id} initiated.")

    return new_words


async def detect_lemma_pos_pair_with_multiple_occurrences(vocabulary_dict):
    # If any value in words has more than 5 words, logger it
    lemma_pos_pairs_has_more_than_5_occurrences = 0
    for key, value in vocabulary_dict.items():
        if len(value) > 5:
            lemma_pos_pairs_has_more_than_5_occurrences += 1


async def initiate_vocabulary(user_id: int, session: AsyncSession) -> Dict[str, List[List[Union[int, str]]]]:
    """
    If the user has no vocabulary, create one.
    The vocabulary is a dictionary with lemma+pos as key, a list of (id, lemma) as value.
    Args:
        user_id: User id
        session: AsyncSession
    """
    logger.debug(f"Initiating vocabulary for user {user_id} ...")
    stmt = select(User).where(User.id == user_id)
    user = (await session.execute(stmt)).scalar_one()

    stmt = select(Word).where(Word.id.in_(user.word_ids))
    words = (await session.execute(stmt)).scalars().all()

    # Create dictionary with lemma+pos as key, a list of (id, lemma) as value
    vocabulary_dict: Dict[str, List[List[Union[int, str]]]] = {}
    for word in words:
        # Only add English words to the vocabulary for now
        if word and word.language == "en":
            # for safety
            assert (word.cefr not in ["A1", "A2",
                                      "B1"]), f"[CEFR Error] Word {word.lemma} ({word.pos}) with CEFR {word.cefr} should not exist."

            key = f"{word.lemma};{word.pos}"
            if key not in vocabulary_dict:
                vocabulary_dict[key] = []
            vocabulary_dict[key].append([word.id, word.lemma])

    vocabulary_entry = Vocabulary(
        user_id=user_id,
        vocabulary=vocabulary_dict
    )
    session.add(vocabulary_entry)
    await session.flush()

    user.vocabulary_id = vocabulary_entry.id
    session.add(user)
    await session.flush()
    await session.commit()

    return vocabulary_dict


async def initiate_families(user_id: int, session: AsyncSession) -> None:
    logger.info(f"Initiating families for user {user_id}...")
    stmt = select(Vocabulary).where(Vocabulary.user_id == user_id)
    vocabulary_dict = (await session.execute(stmt)).scalar_one().vocabulary

    families = defaultdict(list)
    for key, id_lemma_lists in vocabulary_dict.items():
        lemma, _ = key.split(";")
        for word_id, _ in id_lemma_lists:
            families[lemma].append(word_id)

    for lemma, word_ids in families.items():
        family_entry = Families(
            user_id=user_id,
            lemma=lemma,
            word_ids=word_ids,
        )
        session.add(family_entry)

    await session.flush()
    await session.commit()
    logger.info(f"Families for user {user_id} initiated.")
    logger.info(f"Total families created: {len(families)}")


async def update_family_with_new_words(
        user_id: int,
        new_words: Dict[str, List[List[Union[int, str]]]],
        session: AsyncSession) -> None:
    logger.info(f"Updating Families for user {user_id} with new words.")

    stmt = select(Families).where(Families.user_id == user_id)
    existing_families = {
        family.lemma: family for family in (await session.execute(stmt)).scalars().all()
    }

    for lemma_pos, id_lemma_lists in new_words.items():
        lemma, _ = lemma_pos.split(";")
        word_ids = [word_id for word_id, _ in id_lemma_lists]

        if lemma in existing_families:
            family = existing_families[lemma]
            existing_word_ids = set(family.word_ids)
            new_word_ids = [wid for wid in word_ids if wid not in existing_word_ids]
            if new_word_ids:
                family.word_ids.extend(new_word_ids)
                session.add(family)
        else:
            new_family = Families(
                user_id=user_id,
                lemma=lemma,
                word_ids=word_ids,
            )
            session.add(new_family)

    await session.flush()
    await session.commit()
    logger.info(f"Families for user {user_id} updated with new words.")


async def initiate_graph(user_id: int, session: AsyncSession,
                         similarity_threshold: float = 0.3, k: int = 5) -> None:
    """
    Build a graph connecting families based on vector similarity.
    When similarity_threshold is 0.0, all edges are added.
    When similarity_threshold is not 0.0, only edges with similarity above the threshold are added and the number of
    edges per node is restricted to k.
    similarity_threshold has a default value of 0.30 and k has a default value of 5.
    Args:
        user_id: The ID of the current user.
        session: The database session.
        similarity_threshold: Minimum similarity to create an edge.
        k: Maximum number of edges per node.

    Returns:
        None: The graph is stored in the database.
    """
    logger.info(f"Building graph for user {user_id} with similarity_threshold {similarity_threshold}...")

    stmt = select(Graph).where(Graph.user_id == user_id)
    existing_graph = (await session.execute(stmt)).scalar_one_or_none()

    if existing_graph:
        logger.info(f"Graph already exists for user {user_id}")
        graph_entry = existing_graph
    else:
        graph_entry = Graph(user_id=user_id)
        session.add(graph_entry)
        await session.flush()

    stmt = select(Families).where(Families.user_id == user_id)
    families = (await session.execute(stmt)).scalars().all()

    stmt = select(GraphNode).where(GraphNode.graph_id == graph_entry.id)
    existing_nodes = {node.lemma: node for node in (await session.execute(stmt)).scalars().all()}

    # TODO: consider, in the future, if we delete the standalone nodes, or we keep them.
    nodes_dict = {}
    for family in families:
        if family.lemma in existing_nodes:
            node = existing_nodes[family.lemma]
            if set(node.word_ids) != set(family.word_ids):
                node.word_ids = list(set(node.word_ids + family.word_ids))
                session.add(node)
            nodes_dict[family.lemma] = node
        else:
            node = GraphNode(
                graph_id=graph_entry.id,
                lemma=family.lemma,
                word_ids=family.word_ids,
                mastery=0.5,
                acquired=False
            )
            session.add(node)
            nodes_dict[family.lemma] = node

    await session.flush()

    if len(families) == 0:
        logger.info(f"No families found for user {user_id}.")
        return

    vectors, relation = await collect_vectors(families, session, similarity_threshold)

    if vectors.size == 0:
        logger.error("No valid vectors found for any family. Please check.")
        return

    logger.debug(f"families shape: {len(families)}")
    logger.debug(f"vectors shape: {vectors.shape}")

    similarity_matrix = await compute_similarity_matrix(vectors)

    weighted_adj_list = await _build_adjacency_list(families, relation, similarity_matrix, similarity_threshold, k)

    await create_edges_in_db(session, graph_entry, nodes_dict, weighted_adj_list)

    logger.info(
        f"Graph for user {user_id} initialized successfully with {len(families)} nodes and"
        f" {len(weighted_adj_list)} edges.")


async def collect_vectors(families, session, similarity_threshold):
    vectors = []
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
            vectors_for_family = []
            for word_id in family.word_ids:
                result = await session.execute(select(Word).where(Word.id == word_id))
                word = result.scalar_one()
                if word.vector is not None:
                    vectors_for_family.append(word.vector)
                else:
                    logger.info(f"Word {word.lemma} has no vector.")
            if vectors_for_family:
                vectors.append(np.mean(vectors_for_family, axis=0))
            else:
                logger.warning(f"Family {family.lemma} has no valid word vectors and will be skipped.")
    return vectors, relation


async def compute_similarity_matrix(vectors):
    logger.info(f"Computing similarity.")
    norms = np.linalg.norm(vectors, axis=1)
    if np.any(norms == 0):
        logger.error("Encountered zero norm vector during normalization.")
        return

    normalized_vectors = vectors / norms[:, np.newaxis]
    similarity_matrix = np.dot(normalized_vectors, normalized_vectors.T)
    logger.debug("Shape of vectors {}".format(vectors.shape))
    logger.debug("Shape of norms {}".format(norms.shape))
    logger.debug(f"Similarity matrix shape: {similarity_matrix.shape}")
    return similarity_matrix


async def _build_adjacency_list(families, relation, similarity_matrix, similarity_threshold, k):
    weighted_adj_list = []
    degree = defaultdict(int)

    if similarity_threshold != 0.0:
        family_lemma_list = [family.lemma for family in families]
        relatives = {}

        for i, f1 in enumerate(family_lemma_list):
            buffer = []
            for f2 in family_lemma_list[i + 1:]:
                if f1 == f2:
                    continue
                pairs = list(itertools.product(relation[f1], relation[f2]))
                for x, y in pairs:
                    if x >= len(similarity_matrix) or y >= len(similarity_matrix):
                        logger.warning(f"Skipping out-of-bounds index: x={x}, y={y}")
                        continue
                score = max(similarity_matrix[x][y] for x, y in pairs)
                if score > similarity_threshold:
                    buffer.append((f1, f2, min(1.0, score)))
            relatives[f1] = sorted(buffer, key=lambda x: -x[2])

        for f, edges in relatives.items():
            for e in edges:
                if degree[e[0]] < k and degree[e[1]] < k:
                    weighted_adj_list.append(e)
                    degree[e[0]] += 1
                    degree[e[1]] += 1
    else:
        family_lemma_list = [family.lemma for family in families]
        num_families = len(family_lemma_list)
        for i, f1 in tqdm(enumerate(family_lemma_list), total=num_families):
            for j, f2 in enumerate(family_lemma_list[i:]):
                j += i
                if f1 == f2:
                    continue
                if similarity_matrix[i][j] > similarity_threshold:
                    weighted_adj_list.append((f1, f2, similarity_matrix[i][j]))
    return weighted_adj_list

    # # Build the graph using networkx
    # graph = nx.Graph()
    # graph.add_nodes_from([family.lemma for family in families])
    # graph.add_weighted_edges_from(weighted_adj_list)
    # logger.debug(f"Graph has {graph.number_of_nodes()} nodes and {graph.number_of_edges()} edges.")
    # nx.set_node_attributes(graph, 0.5, "mastery")
    # nodes = sorted(graph.nodes(), key=str)
    # logger.debug(f"Print all the nodes: {nodes}")


async def create_edges_in_db(session, graph_entry, nodes_dict, weighted_adj_list):
    count = 0
    for node1_lemma, node2_lemma, weight in weighted_adj_list:
        stmt1 = select(GraphNode).where(GraphNode.graph_id == graph_entry.id, GraphNode.lemma == node1_lemma)
        stmt2 = select(GraphNode).where(GraphNode.graph_id == graph_entry.id, GraphNode.lemma == node2_lemma)
        node1 = (await session.execute(stmt1)).scalar_one_or_none()
        node2 = (await session.execute(stmt2)).scalar_one_or_none()

        if node1 and node2:
            edge = GraphEdge(
                graph_id=graph_entry.id,
                node1_id=node1.id,
                node2_id=node2.id,
                weight=weight
            )
            session.add(edge)
            count += 1
        else:
            logger.error(f"Node {node1_lemma} or {node2_lemma} not found in graph {graph_entry.id}")
    await session.flush()
    await session.commit()
    logger.debug(f"Graph edges created: {count == len(weighted_adj_list)}")


async def update_graph(
        user_id: int,
        session: AsyncSession,
        similarity_threshold: float = 0.3,
        k: int = 5,
):
    """
    Update the graph for a user by adding new nodes, updating edges, and recalculating top-k edges.

    Args:
        user_id: ID of the user whose graph is being updated.
        session: The database session.
        similarity_threshold: Minimum similarity required to create an edge.
        k: Maximum number of edges allowed per node.

    Returns:
        None: Updates the database in-place.
    """
    logger.info(f"Updating graph for user {user_id} with similarity threshold {similarity_threshold}...")

    stmt = select(Graph).where(Graph.user_id == user_id)
    graph_entry = (await session.execute(stmt)).scalar_one_or_none()
    logger.debug(f"Graph entry: {graph_entry.id}, {graph_entry.user_id}")

    if not graph_entry:
        logger.info(f"No existing graph found for user {user_id}, initiating new graph...")
        await initiate_graph(user_id, session, similarity_threshold, k)
        return

    stmt = select(GraphNode).where(GraphNode.graph_id == graph_entry.id)
    existing_nodes = {node.lemma: node for node in (await session.execute(stmt)).scalars().all()}

    stmt = select(Families).where(Families.user_id == user_id)
    current_families = {family.lemma: family for family in (await session.execute(stmt)).scalars().all()}

    nodes_dict = {}
    for lemma, family in current_families.items():
        if lemma in existing_nodes:
            node = existing_nodes[lemma]
            existing_word_ids = node.word_ids if isinstance(node.word_ids, list) else list(node.word_ids)
            if set(existing_word_ids) != set(family.word_ids):
                node.word_ids = list(set(existing_word_ids + family.word_ids))
                session.add(node)
            nodes_dict[lemma] = node
        else:
            new_node = GraphNode(
                graph_id=graph_entry.id,
                lemma=lemma,
                word_ids=family.word_ids,
                mastery=0.5,
                acquired=False
            )
            session.add(new_node)
            nodes_dict[lemma] = new_node

    await session.flush()
    logger.debug(f"Nodes updated in the graph.")

    vectors, relation = await collect_vectors(current_families.values(), session, similarity_threshold)

    if (isinstance(vectors, list) and not vectors) or (isinstance(vectors, np.ndarray) and len(vectors) == 0):
        logger.error("No valid vectors found for any family. Please check.")
        return

    # Remove all existing edges for this graph and recompute. So that we captured all the potential new contexts for
    # existing <root word, POS> pairs.
    stmt = delete(GraphEdge).where(GraphEdge.graph_id == graph_entry.id)
    await session.execute(stmt)
    logger.debug(f"Existing edges removed from the graph.")

    similarity_matrix = await compute_similarity_matrix(vectors)

    weighted_adj_list = await _build_adjacency_list(current_families.values(), relation, similarity_matrix,
                                                    similarity_threshold, k)

    await create_edges_in_db(session, graph_entry, nodes_dict, weighted_adj_list)

    graph_entry.last_updated = func.now()
    session.add(graph_entry)
    await session.commit()

    logger.info(
        f"Graph for user {user_id} updated successfully. Now, it has {len(nodes_dict)} nodes and {len(weighted_adj_list)} edges.")
