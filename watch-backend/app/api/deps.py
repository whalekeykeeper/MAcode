from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import logger
from app.core.session import async_session


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    logger.debug("Getting database session")
    async with async_session() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"Session error: {str(e)}. Rolling back transaction.")
            await session.rollback()
            raise
        finally:
            await session.close()
            logger.debug("Database session closed")

# async def get_current_user(
#         session: AsyncSession = Depends(get_session),
#         uuid: Optional[str] = Header(None)
# ) -> User:
#     logger.debug(f"Getting user for UUID: {uuid}")
#     if not uuid:
#         raise HTTPException(status_code=400, detail="uuid header is required")
#
#     # Try to get existing user
#     stmt = select(User).where(User.uuid == uuid)
#     user = (await session.execute(stmt)).scalar_one_or_none()
#
#     # If user doesn't exist, raise an error
#     if not user:
#         raise HTTPException(status_code=401, detail="Invalid user in get_current_user in deps.py")
#
#     return user
