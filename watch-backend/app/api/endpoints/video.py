# /app/api/endpoints/video.py

import re
import time
from pathlib import Path

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi import Request
from fastapi.responses import FileResponse
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.logger import logger
from app.core.utils.video_chosen_words_from_line_processor import address_words_in_line
from app.core.utils.video_subtitles_downloader import get_ytb_id
from app.core.video_service import get_existing_video, ensure_bilingual_subtitles, current_user_has_watched, \
    process_existed_video_for_new_user, process_new_video
from app.models import User, Video
from app.schemas.requests import VideoRequest, VideoChosenWordsRequest
from app.schemas.responses import VideoResponse, VideoChosenWordsResponse

router = APIRouter()


@router.post("/", response_model=VideoResponse)
async def process_video(
        video_request: VideoRequest,
        uuid: str = Header(...),
        session: AsyncSession = Depends(deps.get_session),
):
    """
    Process a video request, download, parse, and store data.
    """
    stmt = select(User).where(User.uuid == uuid)
    user = (await session.execute(stmt)).scalar_one_or_none()
    if not user:
        logger.warning(f"User not found. Creating a new user for uuid={uuid}")
        user = User(uuid=uuid, video_ids=[], word_ids=[])
        session.add(user)
        await session.flush()

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

        ###
        try:
            ytb_id = get_ytb_id(url)
        except ValueError as e:
            logger.warning(f"Invalid YouTube URL received: {url}")
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Transaction failed: {str(e)}")
            await session.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to process video request: {str(e)}")
        finally:
            elapsed_time = time.time() - start_time
            logger.info(f"Elapsed time: {elapsed_time:.2f} seconds")

        logger.debug(f"Extracted YouTube ID: {ytb_id}")
        ###

        static_folder = Path(__file__).parent.parent.parent.parent / "static"

        existing_video = await get_existing_video(ytb_id, session)
        if existing_video:
            logger.info(f"Video {ytb_id} already exists in the database.")
            await ensure_bilingual_subtitles(existing_video, static_folder, session)
            if await current_user_has_watched(user.id, existing_video.id, session):
                logger.info(f"User {user.id} has already watched video {existing_video.id}.")
                return VideoResponse(
                    id=existing_video.id,
                    ytb_id=existing_video.ytb_id,
                    url=existing_video.url,
                    video_path=existing_video.video_path,
                    vtt_path=existing_video.vtt_path,
                    uuid=user.uuid
                )
            await process_existed_video_for_new_user(user, existing_video.id, session)
            logger.info(f"Processed existing video {ytb_id} for user {user.id}.")
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
            new_video = await process_new_video(url, ytb_id, static_folder, user, session)
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
        video_id: int,
        request: Request,
        session: AsyncSession = Depends(deps.get_session),
):
    """
    Stream a video file to the client.
    
    Args:
        video_id: Database ID of the video (not YouTube ID)
        request: HTTP request object
        session: Database session
        
    Returns:
        FileResponse: Video file stream
    """
    stmt = select(Video).where(Video.id == video_id)
    video = (await session.execute(stmt)).scalar_one_or_none()

    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    video_path = Path(video.video_path)
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="Video file not found")
    file_size = video_path.stat().st_size
    headers = {}
    range_header = request.headers.get('range')
    if range_header:
        byte1, byte2 = 0, None
        m = re.search(r'bytes=(\d+)-(\d*)', range_header)
        if m:
            byte1 = int(m.group(1))
            if m.group(2):
                byte2 = int(m.group(2))

        length = file_size - byte1 if byte2 is None else byte2 - byte1 + 1
        with open(video_path, 'rb') as f:
            f.seek(byte1)
            data = f.read(length)

        headers['Content-Range'] = f'bytes {byte1}-{byte1 + length - 1}/{file_size}'
        return StreamingResponse(iter([data]), media_type="video/mp4", status_code=206, headers=headers)

    return FileResponse(video_path, media_type='video/mp4', headers={"Access-Control-Allow-Origin": "*"})


@router.get("/vtt/{video_id}")
async def get_subtitles(
        video_id: int,
        session: AsyncSession = Depends(deps.get_session),
):
    """
    Stream subtitle file to the client.
    
    Args:
        video_id: Database ID of the video (not YouTube ID)
        session: Database session
        
    Returns:
        FileResponse: VTT subtitle file
    """
    stmt = select(Video).where(Video.id == video_id)
    video = (await session.execute(stmt)).scalar_one_or_none()

    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    if not Path(video.vtt_path).exists():
        raise HTTPException(status_code=404, detail="VTT file not found")

    logger.debug(video.vtt_path[-18:])
    return FileResponse(video.vtt_path, filename=video.vtt_path[-18:])


@router.post("/chosen", response_model=VideoChosenWordsResponse)
async def record_chosen_words(
        chosen_request: VideoChosenWordsRequest,
        uuid: str = Header(...),
        session: AsyncSession = Depends(deps.get_session),
) -> VideoChosenWordsResponse:
    """
    Collect user's space-bar-pressing actions, analyze and store interesting chosen words in database.
    This endpoint is called when the user presses the space bar.

    Note this endpoint has nothing with the "acquired" changes in the word list view (the page to show the chosen words
     for the current user).

    Args:
        chosen_request: VideoChosenWordsRequest, the request object
        uuid: str, the user's uuid
        session: Database session

    Returns:
        VideoChosenWordsResponse: The chosen words response in a list of tuples
    """
    stmt = select(User).where(User.uuid == uuid)
    user = (await session.execute(stmt)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="Can't find the user with the given UUID {uuid} "
                                                    "when recording chosen words.")
    # TODO: Think about the frontend, could the line id be offered? If yes, can use the line id directly to get line.
    chosen_words = await address_words_in_line(
        chosen_request.start_time,
        chosen_request.end_time,
        chosen_request.video_id,
        user_id=user.id,
        session=session
    )
    logger.debug(f"===== Start to print: Print the chosen word:")
    for word in chosen_words:
        logger.debug(f"=====Chosen word: {word}")
    logger.debug(f"===== Printing ends.")
    if len(chosen_words) != 0:
        return VideoChosenWordsResponse(
            chosen_words=chosen_words,
        )
    else:
        logger.info(f"No chosen words found or the chosen word is already in database.")
        return VideoChosenWordsResponse(
            chosen_words=[],
        )


@router.get("/test")
async def test_endpoint():
    return {"message": "Video endpoint is working"}
