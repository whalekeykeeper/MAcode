from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.gap_filling_service import generate_gap_filling_exercises
from app.core.logger import logger
from app.models import User, Graph, GapFillingTable, GraphNode, GraphEdge
from app.schemas.requests import ExerciseResultUpdateRequest
from app.schemas.responses import GapFillingResponse, ExerciseResultUpdateResponse

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


@router.get("/", response_model=list[GapFillingResponse], status_code=201)
async def generate_exercises(
        uuid: str = Header(...),
        session: AsyncSession = Depends(deps.get_session),
):
    """
    Generate multi-gap-filling exercises, update GapFilling table,
    and send the exercises in ready-order to the frontend.
    """
    stmt = select(User).where(User.uuid == uuid)
    user = (await session.execute(stmt)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid user when generating gap-filling exercises")

    stmt = select(Graph).where(Graph.user_id == user.id)
    graph = (await session.execute(stmt)).scalar_one_or_none()
    if not graph:
        raise HTTPException(status_code=401, detail="Invalid graph when generating gap-filling exercises")

    logger.info(f"Generating gap-filling exercises for user {user.id} and graph {graph.id}")
    exercises = await generate_gap_filling_exercises(user.id, graph.id, session)

    return exercises


@router.post("/result", status_code=201)
async def exercise_result_update(
        exercise_results: list[ExerciseResultUpdateRequest],
        uuid: str = Header(...),
        session: AsyncSession = Depends(deps.get_session),
):
    """
    Frontend sends user's answers to the backend to update the according mastery score in GraphNode table.
    And return the statistics to the frontend.
    """
    stmt = select(User).where(User.uuid == uuid)
    user = (await session.execute(stmt)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid user when updating exercise results")

    stmt = select(Graph).where(Graph.user_id == user.id)
    graph = (await session.execute(stmt)).scalar_one_or_none()
    if not graph:
        raise HTTPException(status_code=401, detail="Invalid graph when generating exercise results")

    # Update the GraphNode table and the GapFilling table
    correct_number = 0
    for exercise in exercise_results:
        if exercise.correct_or_not:
            mastery_score_change_param = 0.3
            correct_or_not = True
            correct_number += 1
        else:
            mastery_score_change_param = -0.3
            correct_or_not = False

        stmt = select(GraphNode).where(GraphNode.id == exercise.node_id)
        node = (await session.execute(stmt)).scalar_one_or_none()
        if not node:
            raise HTTPException(status_code=404, detail="Node not found when updating exercise results")
        logger.debug(f"-----\nNode {node.lemma} with id {node.id} \noriginal mastery: {node.mastery}.")
        # The formula is: new_mastery = old_mastery +- old_mastery * change_mastery_score
        node.mastery += node.mastery * mastery_score_change_param
        if node.mastery > 0.99:
            node.mastery = 0.99
        logger.debug(f"new mastery: {node.mastery}.")
        session.add(node)
        await session.flush()

        # Spread the activation of mastery score to direct neighboring nodes.
        stmt = select(GraphEdge).where(GraphEdge.node1_id == node.id)
        edges = (await session.execute(stmt)).scalars().all()
        neighbors = {}  # {node_id: weight}
        for edge in edges:
            if edge.node2_id == node.id:
                neighbors[edge.node1_id] = edge.weight
            else:
                neighbors[edge.node2_id] = edge.weight
        for neighbor_id, weight in neighbors.items():
            stmt = select(GraphNode).where(GraphNode.id == neighbor_id)
            neighbor = (await session.execute(stmt)).scalar_one_or_none()
            logger.debug(
                f"Node {node.lemma} with id {node.id} spread activation to node {neighbor.lemma} with neighbor_id "
                f"{neighbor_id}, \noriginal mastery: {neighbor.mastery}.")
            # The formula is: new_mastery = old_mastery +- neighbor.mastery* change_mastery_score * weight
            neighbor.mastery += neighbor.mastery * mastery_score_change_param * weight
            if neighbor.mastery > 0.99:
                neighbor.mastery = 0.99
            logger.debug(f"new mastery: {neighbor.mastery}.")
            session.add(neighbor)
            await session.flush()

        stmt = select(GapFillingTable).where(GapFillingTable.id == exercise.exercise_id)
        gap_filling = (await session.execute(stmt)).scalar_one_or_none()
        if not gap_filling:
            raise HTTPException(status_code=404, detail="GapFilling table not found when updating exercise results")
        gap_filling.correct_or_not = correct_or_not
        session.add(gap_filling)
        await session.flush()
    correct_rate = correct_number / len(exercise_results)
    response = ExerciseResultUpdateResponse(exercise_amount=len(exercise_results), correct_amount=correct_number,
                                            correct_rate=correct_rate)
    logger.info(f"User {user.id} updated {len(exercise_results)} exercises, {correct_number} correct, "
                f"correct rate: {correct_rate}")

    await session.commit()
    return response
