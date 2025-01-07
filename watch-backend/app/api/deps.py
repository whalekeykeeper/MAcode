from typing import AsyncGenerator, Optional

from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import logger
from app.core.session import async_session
from app.models import User


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


async def get_current_user(
        session: AsyncSession = Depends(get_session),
        x_user_uuid: Optional[str] = Header(None)
) -> User:
    logger.debug(f"Getting user for UUID: {x_user_uuid}")
    if not x_user_uuid:
        raise HTTPException(status_code=400, detail="X-User-UUID header is required")

    # Try to get existing user
    stmt = select(User).where(User.uuid == x_user_uuid)
    user = (await session.execute(stmt)).scalar_one_or_none()

    # If user doesn't exist, create new user but don't commit here
    if not user:
        logger.info(f"Creating new user with UUID: {x_user_uuid}")
        user = User(uuid=x_user_uuid)
        session.add(user)

    return user
