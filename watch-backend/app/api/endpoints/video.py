# /app/api/endpoints/video.py

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api import deps
from app.core.bilingual_subtitle_creator import create_bilingual_vtt
from app.core.logger import logger
from app.core.subtitle_processor import SubtitleProcessor
from app.core.video_subtitles_downloader import download_video_and_subtitles
from app.core.video_subtitles_downloader import (
    get_ytb_id
)
from app.models import User, Video, UserVideoAssociation
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

    try:
        async with session.begin():
            # Check if ytb_id already in the database.
            stmt_video = select(Video).where(Video.ytb_id == ytb_id)
            existing_video = (await session.execute(stmt_video)).scalar_one_or_none()

            # Try to get existing video
            existing_video = await _get_existing_video(ytb_id, session)

            if existing_video:
                # Ensure bilingual subtitles exist
                await _ensure_bilingual_subtitles(existing_video, static_folder, session)

                # Check if current user has watched this video
                if not await _has_user_watched_video(current_user.id, existing_video.id, session):
                    await _process_existed_video_for_new_user(
                        current_user, existing_video.id, session
                    )

                return existing_video

            # Handle new video
            return await _process_new_video(
                url, ytb_id, static_folder, current_user, session
            )

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process video request: {str(e)}"
        )


async def _get_existing_video(ytb_id: str, session: AsyncSession) -> Optional[Video]:
    """Get video if it exists in database."""
    stmt = select(Video).where(Video.ytb_id == ytb_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def _ensure_bilingual_subtitles(
        video: Video,
        static_folder: str,
        session: AsyncSession
):
    """Ensure bilingual subtitles exist for the video."""
    bilingual_vtt_path = f"{static_folder}/{video.ytb_id}/{video.ytb_id}_bilingual.vtt"
    if not Path(bilingual_vtt_path).exists():
        video.vtt_path = create_bilingual_vtt(video.ytb_id, static_folder)
        session.add(video)
        logger.info(
            f"Bilingual subtitles created for video {video.ytb_id}. Check why the bilingual subtitle isnot created.")


async def _has_user_watched_video(
        user_id: int,
        video_id: int,
        session: AsyncSession
) -> bool:
    """Check if user has already watched the video."""
    stmt = select(UserVideoAssociation).where(
        UserVideoAssociation.user_id == user_id,
        UserVideoAssociation.video_id == video_id
    )
    return bool((await session.execute(stmt)).scalar_one_or_none())


async def _process_existed_video_for_new_user(
        user: User,
        video_id: str,
        session: AsyncSession
):
    """Process existed video for user who hasn't watched it before."""
    # Create association
    new_assoc = UserVideoAssociation(
        user_id=user.id,
        video_id=video_id
    )
    session.add(new_assoc)

    # Process subtitles only for user associations
    subtitle_processor = SubtitleProcessor()
    await subtitle_processor.process_subtitles(
        video_id=video_id,
        user_uuid=user.uuid,
        session=session,
        existed_video_for_unwatched_user=True
    )


async def _process_new_video(
        url: str,
        ytb_id: str,
        static_folder: str,
        user: User,
        session: AsyncSession
) -> Video:
    """Download and process new video."""
    try:
        # Download video and create subtitles
        download_video_and_subtitles(ytb_id, url, static_folder)
        bilingual_vtt_path = create_bilingual_vtt(ytb_id, static_folder)

        # Create video entry
        new_video = Video(
            url=url,
            ytb_id=ytb_id,
            video_path=f"{static_folder}/{ytb_id}/{ytb_id}.mp4",
            vtt_path=bilingual_vtt_path,
        )
        session.add(new_video)
        await session.flush()

        # Create user-video association
        new_assoc = UserVideoAssociation(
            user_id=user.id,
            video_id=new_video.id
        )
        session.add(new_assoc)

        # Process subtitles for all tables
        subtitle_processor = SubtitleProcessor()
        await subtitle_processor.process_subtitles(
            video_id=new_video.id,
            user_uuid=user.uuid,
            session=session
        )

        return new_video

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process new video: {str(e)}"
        )


@router.get("/stream/{video_id}")
async def stream_video(
        video_id: str,
        session: AsyncSession = Depends(deps.get_session),
        current_user: User = Depends(deps.get_current_user),
):
    """Streams the video.
    video_id is the id in Video table, not the ytb_id."""

    # ToDo: delete the following code section for checking if the current user has association with this given video.
    stmt = select(UserVideoAssociation).where(
        UserVideoAssociation.user_id == current_user.id,
        UserVideoAssociation.video_id == video_id
    )
    in_user_video_association = (await session.execute(stmt)).scalar_one_or_none()
    if not in_user_video_association:
        logger.error(f"User {current_user.id} is not in the UserVideoAssociation with video id: {video_id}")

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

    # ToDo: delete the following code section for checking if the current user has association with this given video.
    stmt = select(UserVideoAssociation).where(
        UserVideoAssociation.user_id == current_user.id,
        UserVideoAssociation.video_id == video_id
    )
    in_user_video_association = (await session.execute(stmt)).scalar_one_or_none()
    if not in_user_video_association:
        logger.error(f"User {current_user.id} is not in the UserVideoAssociation with video id: {video_id}")

    # Get VTT path
    stmt = select(Video).where(Video.id == video_id)
    video = (await session.execute(stmt)).scalar_one_or_none()

    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    if not Path(video.vtt_path).exists():
        raise HTTPException(status_code=404, detail="VTT file not found")

    return FileResponse(video.vtt_path, filename=video.vtt_path[-18:])
