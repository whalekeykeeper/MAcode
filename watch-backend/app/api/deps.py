from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.session import async_session
from fastapi import Depends, Header, HTTPException, Query
from sqlalchemy import select
from typing import Optional
from app.models import User


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session


async def get_current_user(
    uuid: str = Query(...),
    session: AsyncSession = Depends(get_session)
) -> User:
    """Dependency to get current user from UUID query parameter."""
    stmt = select(User).where(User.uuid == uuid)
    user = (await session.execute(stmt)).scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=400,
            detail="Invalid user UUID. Please provide a valid UUID."
        )
    
    return user
