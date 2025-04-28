from fastapi import APIRouter, Depends, HTTPException, Header, Body
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.logger import logger
from app.models import ChosenWords, GraphNode, User, Graph, Word

"""
This file contains endpoints to show a collection of words as a table. Word data is sent with word id.
This table shows (checkbox, word, word_in_another_language_from_bilingual_subtitle, sentence) in a table with 4 columns.
The words are fetched from the database from the "chosen_words" table.
The order is from the least mastery score. If the mastery score is the same, the order is from the earliest chosen time.
The checkbox "marked_as_learned" is used to let the user eliminate the words from generating exercises manually.
"""

router = APIRouter()


@router.get("/")
async def get_word_list(
        uuid: str = Header(...),
        session: AsyncSession = Depends(deps.get_session),
):
    """
    A function to get the word list from the database
    """
    stmt = select(User).where(User.uuid == uuid)
    user = (await session.execute(stmt)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid user")
    user_id = user.id

    try:
        # Fetch words from ChosenWords table when its "marked_as_learned" field is False,
        # Order from the latest record time.
        # If time is the same, then order from the least mastery score.
        stmt = select(ChosenWords).where(ChosenWords.user_id == user_id)
        chosen_word_list = (await session.execute(stmt)).scalars().all()
        logger.debug(f"The number of chosen words is {len(chosen_word_list)}")
        display_word_list = []
        for chosen_word in chosen_word_list:
            if chosen_word.marked_as_learned:  # If the word is marked as learned, skip it.
                continue
            stmt = select(Graph).where(Graph.user_id == user_id)
            graph = (await session.execute(stmt)).scalar_one_or_none()
            if not graph:
                raise ValueError(
                    f"Graph not found for user {user_id} when update_chosen_in_database.")

            stmt = select(GraphNode).where(GraphNode.lemma == chosen_word.lemma, GraphNode.graph_id == graph.id)
            graph_node = (await session.execute(stmt)).scalar_one_or_none()

            stmt = select(Word).where(Word.id == chosen_word.word_id)
            word = (await session.execute(stmt)).scalar_one_or_none()
            if not word:
                break
            display_word_list.append(
                (chosen_word.word_id, chosen_word.marked_as_learned, word.word, chosen_word.translation,
                 chosen_word.sentence,
                 graph_node.mastery, chosen_word.record_time))
            # logger.debug(
            #     f"Add word {chosen_word.lemma} with id {chosen_word.word_id} "
            #     f"and translation {chosen_word.translation} to the display word list.")

        # Sort the list by record time (from latest on) and mastery score (from least on)
        display_word_list.sort(key=lambda x: (-x[5], x[6]))

        return display_word_list
    except Exception as e:
        logger.error(f"Could not fetch the chosen words' list from ChosenWords table: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/acquired")
async def mark_as_required(
        word_id: int = Body(..., embed=True),
        uuid: str = Header(...),
        session: AsyncSession = Depends(deps.get_session),
) -> None:
    """
    A function to mark the chosen words as acquired
    """
    stmt = select(User).where(User.uuid == uuid)
    user = (await session.execute(stmt)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid user")
    logger.debug(f"User {user.uuid} is found with id {user.id}")

    try:
        logger.debug(f"-----------------Marking word {word_id} as acquired-----------------")
        stmt = select(ChosenWords).where(ChosenWords.word_id == word_id)
        chosen_word = (await session.execute(stmt)).scalar_one_or_none()
        if not chosen_word:
            raise HTTPException(status_code=404, detail="Word not found")

        chosen_word.marked_as_learned = True
        session.add(chosen_word)
        await session.flush()
        logger.debug(f"Marked word {chosen_word.lemma} is marked_as_learned: {chosen_word.marked_as_learned}.")

        logger.debug(f"-----------------Updating the graph-----------------")
        stmt = select(Graph).where(Graph.user_id == user.id)
        graph = (await session.execute(stmt)).scalar_one_or_none()
        if not graph:
            raise ValueError(
                f"Graph not found for user {user_id} when update_chosen_in_database.")

        stmt = select(GraphNode).where(GraphNode.lemma == chosen_word.lemma, GraphNode.graph_id == graph.id)
        graph_node = (await session.execute(stmt)).scalar_one_or_none()
        if not graph_node:
            raise HTTPException(status_code=404, detail="Graph node not found in mark_as_required()")

        logger.debug(f"graph_node {graph_node.lemma} with graph_node.id {graph_node.id} is acquired:"
                     f" {graph_node.acquired}, ")

        graph_node.acquired = True
        graph_node.mastery = 1

        session.add(graph_node)
        await session.flush()
        await session.commit()

        stmt = select(Graph).where(Graph.user_id == user.id)
        graph = (await session.execute(stmt)).scalar_one_or_none()
        if not graph:
            raise ValueError(
                f"Graph not found for user {user_id} when update_chosen_in_database.")

        stmt = select(GraphNode).where(GraphNode.lemma == chosen_word.lemma, GraphNode.graph_id == graph.id)
        graph_node = (await session.execute(stmt)).scalar_one_or_none()
        logger.debug(f"graph_node {graph_node.lemma} is acquired: {graph_node.acquired}, "
                     f"the new mastery is {graph_node.mastery}.")

        # Check the updating in update_graph() for this change.
        return
    except Exception as e:
        logger.error(f"Error marking word {word_id} as acquired: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
