from fastapi import APIRouter

from app.api.endpoints import users, video

api_router = APIRouter()
# api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(video.router, prefix="/videos", tags=["videos"])
# api_router.include_router(
#     translation.router, prefix="/translation", tags=["translation"]
# )
# api_router.include_router(
#     gapfilling.router, prefix="/gap_filling", tags=["gap_filling"]
# )
