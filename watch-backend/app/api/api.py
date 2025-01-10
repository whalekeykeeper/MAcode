from fastapi import APIRouter
from app.api.endpoints.video import router as video_router
from app.api.endpoints.word_list_collection import router as word_list_router
from app.api.endpoints.gap_filling_exercises import router as gap_filling_router
from app.api.endpoints.visualization import router as visualization_router
from app.api.endpoints.users import router as users_router
api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(video_router, prefix="/videos", tags=["videos"])
api_router.include_router(word_list_router, prefix="/word_list", tags=["word_list"])
api_router.include_router(gap_filling_router, prefix="/gap_filling", tags=["gap_filling"])
api_router.include_router(visualization_router, prefix="/visualization", tags=["visualization"])
api_router.include_router(users_router, prefix="/users", tags=["users"])