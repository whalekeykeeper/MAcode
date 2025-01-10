# /app/api/endpoints/video.py

import time
from pathlib import Path

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.logger import logger
from app.core.utils.video_subtitles_downloader import get_ytb_id
from app.core.video_service import get_existing_video, ensure_bilingual_subtitles, current_user_has_watched, \
    process_existed_video_for_new_user, process_new_video
from app.models import User, Video
from app.schemas.requests import VideoRequest
from app.schemas.responses import VideoResponse

router = APIRouter()


@router.post("/", response_model=VideoResponse)
async def process_video(
        video_request: VideoRequest,
        uuid: str = Header(...),
        session: AsyncSession = Depends(deps.get_session),
        current_user: User = Depends(deps.get_current_user),
):
    logger.debug("Starting process_video endpoint")
    if not uuid:
        logger.error("UUID header is missing")
        raise HTTPException(status_code=400, detail="UUID header is required")
    """
    Process a video request and handle subtitle generation.
    
    This endpoint:
    1. Downloads the video if it doesn't exist
    2. Processes subtitles and creates bilingual versions
    3. Updates user's vocabulary and graph representation in database
    
    Returns:
        VideoResponse: The processed video information
    """
    logger.debug(f"Request received with headers: {uuid} and body: {video_request}")
    start_time = time.time()

    stmt = select(User).where(User.uuid == uuid)
    user = (await session.execute(stmt)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid user")

    try:
        url = video_request.video_url
        logger.debug(f"Processing video URL: {url}")
        ytb_id = get_ytb_id(url)
        logger.debug(f"Extracted YouTube ID: {ytb_id}")
        static_folder = Path(__file__).parent.parent.parent.parent / "static"

        existing_video = await get_existing_video(ytb_id, session)
        if existing_video:
            logger.info(f"Video {ytb_id} already exists in the database.")
            await ensure_bilingual_subtitles(existing_video, static_folder, session)
            if await current_user_has_watched(current_user.id, existing_video.id, session):
                logger.info(f"User {current_user.id} has already watched video {existing_video.id}.")
                return VideoResponse(
                    id=existing_video.id,
                    ytb_id=existing_video.ytb_id,
                    url=existing_video.url,
                    video_path=existing_video.video_path,
                    vtt_path=existing_video.vtt_path,
                    uuid=user.uuid
                )
            await process_existed_video_for_new_user(current_user, existing_video.id, session)
            logger.info(f"Processed existing video {ytb_id} for user {current_user.id}.")
            await session.commit()
            return VideoResponse(
                id=existing_video.id,
                ytb_id=existing_video.ytb_id,
                url=existing_video.url,
                video_path=existing_video.video_path,
                vtt_path=existing_video.vtt_path,
                uuid=user.uuid
            )

        else:
            logger.info(f"Video {ytb_id} does not exist in the database. Processing subtitles.")
            new_video = await process_new_video(url, ytb_id, static_folder, current_user, session)
            await session.commit()
            return VideoResponse(
                id=new_video.id,
                ytb_id=new_video.ytb_id,
                url=new_video.url,
                video_path=new_video.video_path,
                vtt_path=new_video.vtt_path,
                uuid=user.uuid
            )

    except Exception as e:
        logger.error(f"Transaction failed: {str(e)}")
        await session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to process video request: {str(e)}")
    finally:
        elapsed_time = time.time() - start_time
        logger.info(f"Elapsed time: {elapsed_time:.2f} seconds")


@router.get("/stream/{video_id}")
async def stream_video(
        video_id: str,
        session: AsyncSession = Depends(deps.get_session),
        current_user: User = Depends(deps.get_current_user),
):
    """
    Stream a video file to the client.
    
    Args:
        video_id: Database ID of the video (not YouTube ID)
        session: Database session
        current_user: Current authenticated user
        
    Returns:
        FileResponse: Video file stream
    """
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
    """
    Stream subtitle file to the client.
    
    Args:
        video_id: Database ID of the video (not YouTube ID)
        session: Database session
        current_user: Current authenticated user
        
    Returns:
        FileResponse: VTT subtitle file
    """
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
