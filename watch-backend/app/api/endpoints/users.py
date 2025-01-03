from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api import deps
from app.models import User
from app.schemas.requests import UserRequest
from app.schemas.responses import UserResponse

router = APIRouter()


@router.post("/user", response_model=UserResponse, status_code=200)
async def get_or_create_user(
        user_request: UserRequest,
        session: AsyncSession = Depends(deps.get_session),
):
    """
    Handle user requests with three possible scenarios:
    1. UUID is None: Create a new user.
    2. UUID exists and matches an entry in the database: Return the user.
    3. UUID exists but does not match any entry: Raise an error.
    """
    user_uuid = user_request.uuid

    async with session.begin():
        if user_uuid is None:
            # Case 1: UUID is None, create a new user
            new_user = User()  # UUID will be generated automatically
            session.add(new_user)
            await session.commit()
            await session.refresh(new_user)
            return UserResponse(uuid=new_user.uuid, exists=False)

        # Case 2 & 3: UUID is provided
        stmt = select(User).where(User.uuid == user_uuid)
        user = (await session.execute(stmt)).scalars().first()

        if user:
            # Case 2: UUID exists in the database
            return UserResponse(uuid=user.uuid, exists=True)

        # Case 3: UUID does not exist in the database
        raise HTTPException(
            status_code=400,
            detail="Provided UUID does not exist. Please check your setup.",
        )
