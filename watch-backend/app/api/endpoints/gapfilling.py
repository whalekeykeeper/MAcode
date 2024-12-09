from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.gap_filling_service import (
    fetch_gap_filling_exercises,
    generate_gap_filling_exercises,
    update_exercise_correctness,
)
from app.schemas.requests import CorrectnessUpdateRequest
from app.schemas.responses import GapFillingResponse

router = APIRouter()


@router.get("/", response_model=list[GapFillingResponse], status_code=200)
async def get_gap_filling_exercises(session: AsyncSession = Depends(deps.get_session)):
    """
    Fetch all gap-filling exercises.
    """
    return await fetch_gap_filling_exercises(session)


@router.post("/generate", response_model=list[GapFillingResponse], status_code=201)
async def generate_exercises(session: AsyncSession = Depends(deps.get_session)):
    """
    Generate gap-filling exercises from translations.
    """
    return await generate_gap_filling_exercises(session)


@router.post("/{exercise_id}/correct", status_code=200)
async def mark_exercise_as_correct(
    exercise_id: int,
    request: CorrectnessUpdateRequest,
    session: AsyncSession = Depends(deps.get_session),
):
    """
    Update correctness frequency for a specific exercise.
    """
    updated_exercise = await update_exercise_correctness(
        session, exercise_id, request.is_correct
    )
    if updated_exercise is None:
        raise HTTPException(status_code=404, detail="Exercise not found")
    return {"message": "Exercise updated successfully", "exercise_id": exercise_id}
