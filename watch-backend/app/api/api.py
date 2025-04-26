from fastapi import APIRouter

from app.api.endpoints.chosen_words import router as chosen_words_router
from app.api.endpoints.cloud import router as cloud_router
from app.api.endpoints.gap_filling_exercises import router as gap_filling_router
from app.api.endpoints.users import router as users_router
from app.api.endpoints.video import router as video_router
from app.api.endpoints.visualization import router as visualization_router

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(video_router, prefix="/videos", tags=["videos"])
api_router.include_router(chosen_words_router, prefix="/chosen_words", tags=["chosen_words"])
api_router.include_router(gap_filling_router, prefix="/gap_filling", tags=["gap_filling"])
api_router.include_router(visualization_router, prefix="/visualization", tags=["visualization"])
api_router.include_router(users_router, prefix="/users", tags=["users"])
api_router.include_router(cloud_router, prefix="/cloud", tags=["cloud"])
