# /app/api/endpoints/video.py

import os
from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import Session
from app import schemas, models


from app.models import Video
from app.schemas.requests import VideoRequest
from app.schemas.responses import VideoResponse

from app.api import deps

from app.core.video_and_subtitles import get_video_id, get_bilingual_vtt
from pathlib import Path

router = APIRouter()


@router.post("/", response_model=VideoResponse, status_code=201)
async def get_new_video(
        new_video: VideoRequest,
        session: AsyncSession = Depends(deps.get_session),
):
    """Creates new video. Only for logged users."""
    url = new_video.video_url
    video_id = get_video_id(url)  # Get YouTube video id

    video_path, vtt_path = get_bilingual_vtt(url)  # Download YouTube video, get subtitles, create bilingual subtitle

    video = Video(video_url=new_video.video_url, video_id=video_id, video_path=video_path, vtt_path=vtt_path)
    session.add(video)
    await session.commit()
    return video


@router.get("/stream/{video_id}")
async def stream_video(video_id: str, session: AsyncSession = Depends(deps.get_session)):
    """Streams the video with the specified video_id."""
    stmt = await session.execute(
        select(Video)
        .where(Video.video_id == video_id)
    )
    video = stmt.scalars().first()

    if video:
        video_file_path = video.video_path
        print(video)
        print(video.video_path)
        print(Path(video_file_path).exists())
        if os.path.exists(video_file_path):
            return StreamingResponse(open(video_file_path, "rb"), media_type="video/mp4")
        else:
            raise HTTPException(status_code=404, detail="Video file not found")
    else:
        raise HTTPException(status_code=404, detail="Video not found")


#
# @router.get("/get-video/{video_id}/", response_model=VideoResponse)
# async def get_video_by_id(video_id: str):
#     # Create an asynchronous database session
#     async with AsyncSession() as session:
#         async with session.begin():
#             # Query the database for the Video record based on video_id as a string
#             statement = select(Video).where(Video.video_id == video_id)
#             result = await session.execute(statement)
#             video = result.scalar_one_or_none()  # Get one or None
#
#             if video is not None:
#                 # If the video is found, return the video_path in the response
#                 return {"video_path": video.video_path}
#             else:
#                 # If no matching record is found, raise an HTTP exception with a 404 status code
#                 raise HTTPException(status_code=404, detail="Video not found")