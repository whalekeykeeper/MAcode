from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.gap_filling_service import (
    fetch_gap_filling_exercises,
    update_exercise_correctness, generate_gap_filling_exercises,
)
from app.schemas.requests import CorrectnessUpdateRequest
from app.schemas.responses import GapFillingResponse

router = APIRouter()

"""
This file contains the FastAPI endpoints for the gap-filling exercises.

Endpoint 1: Generate gap-filling exercises from translations.
The request: user's id or uuid. To be decided. Also let user choose the number of exercises to fetch.
The response: Exercise ids, masked sentences, distractors, correct answers.
Backend task: randomly select nodes from the top candidates, generate exercises, stored in the database. 
Fronend task: display the exercises to the user, highlight the correct answer with green color and incorrect with red.

Endpoint2: Allow button "Show More" to show one sentence before the masked sentence and one sentence after the masked sentence.
The request: user's id or uuid, exercise id.
The response: the exercise with one sentence before and one sentence after the masked sentence.
Backend task: fetch the exercise from the database, find the sentences before and after the masked sentence.
Frontend task: display the exercise with one sentence before and one sentence after the masked sentence.

Endpoint 3: Record the correctness and update the mastery score and the exercises table.
Request: user's id or uuid, exercise id, correctness.
Response: none.
Backend task: update the correctness frequency for a specific exercise, update the mastery score, remove exercises 
when the chosen node's mastery score larger than the mastery_threshold.
Frontend task: none.

Endpoint 4: Review of exercises and statistics. "Show Statistics" button.
Request: user's id or uuid, exercise ids, correctnesses.
Response: none.
Frontend task: display all the dinished exercises to the statistics to the user.
Backend task: fetch the exercises from the database, calculate the statistics.

Endpoint 5: "Retake failed exercises" button to fetch the exercises again.
Request: user's id or uuid.
Response: the same exercises as before but only the failed ones and  in different order.
Backend task: fetch the failed exercises from the database.
Frontend task: display the failed exercises to the user.
"""


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
