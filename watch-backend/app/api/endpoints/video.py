# /app/api/endpoints/video.py

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api import deps
from app.core.subtitle_processor import SubtitleProcessor
from app.core.video_and_subtitles import (
    bilingual_subtitles_exist,
    get_ytb_id
)
from app.models import User, Video, UserVideoAssociation
from app.schemas.requests import VideoRequest
from app.schemas.responses import VideoResponse

router = APIRouter()


@router.post("/", response_model=VideoResponse, status_code=201)
async def get_new_video(
        new_video: VideoRequest,
        session: AsyncSession = Depends(deps.get_session),
        current_user: User = Depends(deps.get_current_user),
):
    """Creates new video and associates it with the user."""
    url = new_video.video_url
    ytb_id = get_ytb_id(url)

    if not bilingual_subtitles_exist(ytb_id):
        raise HTTPException(
            status_code=500,
            detail="Bilingual subtitles do not exist. Please run the script to create them.",
        )

    async with session.begin():
        # Check if video exists
        stmt_video = select(Video).where(Video.url == url)
        existing_video = (await session.execute(stmt_video)).scalar_one_or_none()

        if existing_video:
            # Check if user already has access to this video
            stmt_assoc = select(UserVideoAssociation).where(
                UserVideoAssociation.user_id == current_user.id,
                UserVideoAssociation.video_id == existing_video.id
            )
            existing_assoc = (await session.execute(stmt_assoc)).scalar_one_or_none()

            if not existing_assoc:
                # Create association if it doesn't exist
                new_assoc = UserVideoAssociation(
                    user_id=current_user.id,
                    video_id=existing_video.id
                )
                session.add(new_assoc)
                await session.commit()

            return existing_video

        # Initialize subtitle processor and process new video
        subtitle_processor = SubtitleProcessor()
        vtt_path = await subtitle_processor.process_subtitles(
            video_id=ytb_id,
            static_folder="static",
            user_uuid=current_user.uuid,
            session=session
        )

        # Create new video entry
        new_video_entry = Video(
            url=new_video.video_url,
            ytb_id=ytb_id,
            video_path=f"static/{ytb_id}/{ytb_id}.mp4",
            vtt_path=vtt_path,
        )
        session.add(new_video_entry)
        await session.flush()

        # Create user-video association
        new_assoc = UserVideoAssociation(
            user_id=current_user.id,
            video_id=new_video_entry.id
        )
        session.add(new_assoc)
        await session.commit()

        return new_video_entry


@router.get("/stream/{video_id}")
async def stream_video(
        video_id: str,
        session: AsyncSession = Depends(deps.get_session),
        current_user: User = Depends(deps.get_current_user),
):
    """Streams the video if user has access."""
    # Check access rights
    stmt = select(UserVideoAssociation).where(
        UserVideoAssociation.user_id == current_user.id,
        UserVideoAssociation.video_id == video_id
    )
    has_access = (await session.execute(stmt)).scalar_one_or_none()

    if not has_access:
        raise HTTPException(
            status_code=403,
            detail="Access to this video is forbidden for the current user.",
        )

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
    """Streams the subtitle file if user has access."""
    # Check access rights
    stmt = select(UserVideoAssociation).where(
        UserVideoAssociation.user_id == current_user.id,
        UserVideoAssociation.video_id == video_id
    )
    has_access = (await session.execute(stmt)).scalar_one_or_none()

    if not has_access:
        raise HTTPException(
            status_code=403,
            detail="Access to this video is forbidden for the current user.",
        )

    # Get VTT path
    stmt = select(Video).where(Video.id == video_id)
    video = (await session.execute(stmt)).scalar_one_or_none()

    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    if not Path(video.vtt_path).exists():
        raise HTTPException(status_code=404, detail="VTT file not found")

    return FileResponse(video.vtt_path, filename=video.vtt_path[-18:])
