# /app/api/endpoints/video.py


from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.models import Video, User
from app.schemas.requests import VideoRequest
from app.schemas.responses import VideoResponse

from app.core.video_and_subtitles import get_video_id, get_bilingual_vtt
router = APIRouter()


@router.post("/", response_model=VideoResponse, status_code=201)
async def get_new_video(
        new_video: VideoRequest,
        session: AsyncSession = Depends(deps.get_session),
        current_user: User = Depends(deps.get_current_user),
):
    """Creates new video. Only for logged users."""
    url = new_video.video_url

    video_id = get_video_id(url)  # Get YouTube video id
    get_bilingual_vtt(url)  # Download YouTube video, get subtitles, create bilingual subtitle

    video = Video(video_url=new_video.video_url, video_id=video_id)

    session.add(video)
    await session.commit()
    return video


