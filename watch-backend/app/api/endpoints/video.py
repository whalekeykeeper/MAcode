# /app/api/endpoints/video.py

from pathlib import Path
from typing import List
from typing import Optional

import spacy
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api import deps
from app.core.bilingual_subtitle_creator import create_bilingual_vtt
from app.core.logger import logger
from app.core.subtitle_processor import SubtitleProcessor
from app.core.video_subtitles_downloader import download_video_and_subtitles, get_ytb_id
from app.models import User, Video
from app.models import Word, Vocabulary
from app.schemas.requests import VideoRequest
from app.schemas.responses import VideoResponse

router = APIRouter()


@router.post("/", response_model=VideoResponse, status_code=201)
async def download_and_process_video_and_subtitles(
        new_video: VideoRequest,
        session: AsyncSession = Depends(deps.get_session),
        current_user: User = Depends(deps.get_current_user),
):
    """Process video request with proper transaction management.

    Note: ytb_id is always called ytb_id in the database and in this code base. video_id is
    called id in the database.
    """
    url = new_video.video_url
    ytb_id = get_ytb_id(url)
    static_folder = "static"
    valid_pos = ["NOUN", "VERB", "ADJ", "ADV", "PROPN", "INTJ"]

    try:
        async with session.begin():
            # Check if ytb_id already in the database.
            existing_video = await _get_existing_video(ytb_id, session)

            if existing_video:
                await _ensure_bilingual_subtitles(existing_video, static_folder, session)
                # Check if current user has watched this video
                if await _has_current_user_watched_video(current_user.id, existing_video.id, session):
                    return existing_video
                await _process_existed_video_for_new_user(current_user, existing_video.id, valid_pos, session)
                return existing_video

            else:
                return await _process_new_video(url, ytb_id, static_folder, current_user, valid_pos, session)

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=500, detail=f"Failed to process video request: {str(e)}"
        )


async def _get_existing_video(ytb_id: str, session: AsyncSession) -> Optional[Video]:
    """Get video if it exists in database."""
    stmt = select(Video).where(Video.ytb_id == ytb_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def _ensure_bilingual_subtitles(
        video: Video, static_folder: str, session: AsyncSession
):
    """Ensure bilingual subtitles exist for the video."""
    bilingual_vtt_path = f"{static_folder}/{video.ytb_id}/{video.ytb_id}_bilingual.vtt"
    if not Path(bilingual_vtt_path).exists():
        video.vtt_path = create_bilingual_vtt(video.ytb_id, static_folder)
        session.add(video)
        logger.info(
            f"Bilingual subtitles created for video {video.ytb_id}. Check why the bilingual subtitle isnot created."
        )


async def _has_current_user_watched_video(
        user_id: int, video_id: int, session: AsyncSession
) -> bool:
    """Check if the given user has already watched the video using User table."""
    stmt = select(User.video_ids).where(User.id == user_id)
    user_video_ids = (await session.execute(stmt)).scalar_one_or_none()

    return video_id in user_video_ids if user_video_ids else False


async def _process_existed_video_for_new_user(
        user: User, video_id: int, valid_pos: List[str], session: AsyncSession
):
    """Process existed video for user who hasn't watched it before."""
    # Load the spacy model for English
    nlp_en = spacy.load("en_core_web_lg")

    # Fetch word IDs from Video
    stmt = select(Video.word_ids).where(Video.id == video_id)
    word_ids = (await session.execute(stmt)).scalar_one_or_none()

    if word_ids:
        user.video_ids = list(set(user.video_ids + [video_id]))
        user.word_ids = list(set(user.word_ids + video_word_ids))

        session.add(user)
        await session.flush()

    # Update Vocabulary and Families
    stmt = select(Vocabulary).where(Vocabulary.user_id == user.id)
    vocabulary = (await session.execute(stmt)).scalar_one_or_none()
    if video_word_ids:
        # Update user video and word associations
        if vocabulary:
            vocabulary_dict = vocabulary.to_dict()
            # Iterate over the word_ids from this video and update the word_ids in the current user's Vocabulary,
            # collect all the words which fits the valid_pos and not stop words
            for word_id in word_ids:
                stmt = select(Word).where(Word.id == word_id)
                word = (await session.execute(stmt)).scalar_one_or_none()
                if word and word.language == "en" and not nlp_en.vocab[word.lemma].is_stop and word.pos in valid_pos:
                    key = f"{word.lemma};{word.pos}"
                    if key not in vocabulary_dict:
                        vocabulary_dict[key] = []
                    vocabulary_dict[key].append([word.id, word.lemma])
            session.add(vocabulary)
            await session.flush()

            # If any value in words has more than 5 words, logger it
            for key, value in vocabulary_dict.items():
                if len(value) > 5:
                    logger.info(f"Family {key} has {len(value)} words.")

        else:
            logger.error(f"No vocabulary found for user {user.id}")
            raise HTTPException(status_code=404, detail=f"No vocabulary found for user {user.id}")

    else:
        logger.error(f"Vocabulary not found for user {user.id}")
        raise HTTPException(status_code=404, detail="Vocabulary not found for user with id {user.id}")

    logger.info(f"Updated user {user.id} with video {video_id} and associated words.")


async def _process_new_video(
        url: str, ytb_id: str, static_folder: str, user: User, valid_pos: List[str], session: AsyncSession
) -> Video:
    """Download and process new video."""
    try:
        # Download video and create subtitles
        download_video_and_subtitles(ytb_id, url, static_folder)
        bilingual_vtt_path = create_bilingual_vtt(ytb_id, static_folder)

        # Create video entry, mainly for generating id.
        new_video = Video(
            url=url,
            ytb_id=ytb_id,
            video_path=f"{static_folder}/{ytb_id}/{ytb_id}.mp4",
            vtt_path=bilingual_vtt_path,
        )
        session.add(new_video)
        await session.flush()

        # Process subtitles for all tables for new videos
        subtitle_processor = SubtitleProcessor()
        await subtitle_processor.process_subtitles(
            ytb_id=new_video.ytb_id, user_uuid=user.uuid, valid_pos=valid_pos, session=session
        )

        return new_video

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to process new video: {str(e)}"
        )


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
