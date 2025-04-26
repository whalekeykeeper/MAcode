from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.utils.word_cloud import generate_word_cloud
from app.models import User, Graph
from app.schemas.requests import CloudRequest

router = APIRouter()


@router.post("/")
async def get_word_cloud(uuid: str = Header(...),
                         session: AsyncSession = Depends(deps.get_session)):
    """
    Endpoint to generate a word cloud for a given graph based on mastery scores.

    Args:
        uuid (str): The user UUID.
        cloud_request (CloudRequest): The request object containing min_mastery, max_mastery, and graph_id.
        session (AsyncSession): The database session.

    Returns:
        dict: A message indicating the word cloud has been generated.
    """
    stmt = select(User).where(User.uuid == uuid)
    user = (await session.execute(stmt)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid user when generating word cloud.")

    stmt = select(Graph).where(Graph.user_id == user.id)
    graph = (await session.execute(stmt)).scalar_one_or_none()
    if not graph:
        raise HTTPException(status_code=404, detail="Graph not found for user when generating word cloud.")

    graph_id = graph.id
    try:

        await generate_word_cloud(graph_id, session)
        return {"message": "Word cloud generated successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
