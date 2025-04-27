from datetime import datetime
from pathlib import Path
from typing import List, Tuple

import pandas as pd
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import logger
from app.models import Word, Line, Sentence, ChosenWords, GraphNode, Graph


def load_frequency_lookup() -> dict:
    """
    This method loads the frequency lookup table.
    """
    subtlexus_path = Path(__file__).parent.parent.parent / 'resources' / 'subtlexus.csv'
    logger.debug(f"Loading frequency lookup from {subtlexus_path}.")

    try:
        freq = pd.read_csv(subtlexus_path)
        return {w: f for w, f in freq[['Word', 'Lg10WF']].to_numpy()}
    except FileNotFoundError:
        logger.error(f"Frequency lookup file not found at {subtlexus_path}. Please ensure the file exists.")
        return {}


async def address_words_in_line(start_time: str, end_time: str, video_id: int, user_id: int, session: AsyncSession) -> \
        List[Tuple[int, bool, str, str, str, datetime]]:
    """
    This method extracts the words from the line and returns a list of words.
    And calls update_chosen_in_database to record the chosen word in the database \
    and update the mastery score in the GraphNode table.
    Args:
        start_time: str, the start time of the line in 'HH:MM:SS.sss' format
        end_time: str, the end time of the line in 'HH:MM:SS.sss' format
        video_id: int, the video id
        user_id: int, the user id
        session: AsyncSession, the database session
    Returns:
        List of chosen word which is ready to be displayed: [(word_id, marked_as_learned, lemma, translation, sentence,
        record_time)]
    """
    # Use start_time and end_time as strings to extract the Line from the Line table
    # TODO: the language is hardcoded as 'en' for now, need to be updated to support other languages
    stmt = select(Line).where(Line.start_timestamp == start_time, Line.end_timestamp == end_time,
                              Line.video_id == video_id, Line.language == 'en')
    line = (await session.execute(stmt)).scalar_one_or_none()
    if not line:
        logger.warning(f"Line not found for start_time: {start_time}, end_time: {end_time}, video_id: {video_id}")
        return []
    else:
        logger.debug(f"[Chosen Line Text] Start: {start_time}, End: {end_time}, Text: \"{line.line_text}\"")

    # Extract all the word_ids from the Word table for the line with line_id
    stmt = select(Word).where(Word.line_id == line.id)
    words = (await session.execute(stmt)).scalars().all()

    # Extract graph_id from the Graph table for the user_id
    stmt = select(Graph).where(Graph.user_id == user_id)
    graph = (await session.execute(stmt)).scalar_one_or_none()
    if not graph:
        raise ValueError(f"Graph not found for user_id: {user_id} when addressing words in chosen line.")

    # Only keep words which is in User's Graph
    chosen_words_in_graph = []
    for word in words:
        logger.debug(f"Checking word {word.lemma} in the GraphNode table for user {user_id}.")
        stmt = select(GraphNode).where(
            and_(
                GraphNode.lemma == word.lemma,
                GraphNode.graph_id == graph.id
            )
        )
        graph_node = (await session.execute(stmt)).scalar_one_or_none()
        if not graph_node:
            continue
        chosen_words_in_graph.append(word)

    if not chosen_words_in_graph:
        logger.info(f"No chosen words found in the line with start_time: {start_time}, end_time: {end_time}, "
                    f"video_id: {video_id}.")
        return []

    # TODO: we only use words in the subtlexus database for now.
    # Get the frequency of each word from the frequency lookup table
    frequency_lookup = load_frequency_lookup()
    # Create a list of tuples for the chosen words where each tuple is (word, frequency)
    word_frequency_list = [(word, frequency_lookup.get(word.lemma, 0)) for word in chosen_words_in_graph]
    # Sort the words by frequency
    word_frequency_list.sort(key=lambda x: x[1])

    if word_frequency_list or word_frequency_list[0][1] == 0:
        # Choose the one word with the least frequency
        chosen = [word_frequency_list[0][0]]
    else:
        # If no words are found in the frequency lookup, return all words
        logger.info("No words found in frequency lookup, returning all words.")
        chosen = chosen_words_in_graph

    result = []
    # Record the chosen words in the ChosenWords table, and update the mastery score in the GraphNode table by -0.15
    for word in chosen:
        new_chosen_word = await update_chosen_in_database(user_id=user_id, word=word, session=session)
        if new_chosen_word:
            result.append(new_chosen_word)
    # Note: result can be an empty list if no chosen words are found in the line. 
    return result


async def update_chosen_in_database(user_id: int,
                                    word: Word,
                                    session: AsyncSession,
                                    weight_adjustment_for_chosen_word: float = 0.15) \
        -> Tuple[int, bool, str, str, str, datetime] or None:
    """
    This method update the "marked_as_learned" field in the ChosenWords table, and the "mastery" fields
    in the GraphNode table by -0.15 for each chosen word.
    Args:
        user_id: int, the user id
        word: Word, the word object
        session: AsyncSession, the database session
        weight_adjustment_for_chosen_word: float, the weight adjustment for the chosen word
    Returns:
        A new ChosenWords object: (word_id, marked_as_learned, lemma, translation, sentence, record_time)
        Or None if the word is already in the ChosenWords table.
    """
    # Check if this word's lemma is already in the ChosenWords table.
    # Doesn't have to be the exact same word, just the same lemma.
    stmt = select(ChosenWords).where(ChosenWords.user_id == user_id, ChosenWords.lemma == word.lemma)
    chosen_word = (await session.execute(stmt)).scalar_one_or_none()
    if chosen_word:
        logger.debug(
            f"The word {word.lemma} is already in the ChosenWords table for user {user_id} with id {chosen_word.id} "
            f"when updating the mastery score after chosen a word.")
        return None

    # TODO:For now we save sentence's text in ChosenWords table for convenience. Improve this in the future.
    stmt = select(Line).where(Line.id == word.line_id)
    line = (await session.execute(stmt)).scalar_one_or_none()
    if not line:
        raise ValueError(
            f"Line not found for word {word.lemma} with id {word.id} when update_chosen_in_database.")

    stmt = select(Sentence).where(Sentence.id == line.sentence_id)
    sentence = (await session.execute(stmt)).scalar_one_or_none()
    if not sentence:
        raise ValueError(
            f"Sentence not found for word {word.lemma} with id {word.id} when update_chosen_in_database.")

    stmt = select(Graph).where(Graph.user_id == user_id)
    graph = (await session.execute(stmt)).scalar_one_or_none()
    if not graph:
        raise ValueError(
            f"Graph not found for user {user_id} when update_chosen_in_database.")

    stmt = select(GraphNode).where(GraphNode.lemma == word.lemma, GraphNode.graph_id == graph.id)
    graph_node = (await session.execute(stmt)).scalar_one_or_none()
    if not graph_node:
        raise ValueError(
            f"GraphNode not found for word {word.lemma} with id {word.id} when update_chosen_in_database.")

    # create a new ChosenWords entry and add it to the ChosenWords table
    chosen_word = ChosenWords(user_id=user_id,
                              word_id=word.id,
                              lemma=word.lemma,
                              # TODO: implement for getting translation
                              translation=word.translation,
                              sentence=sentence.sentence_text,
                              marked_as_learned=False,
                              graph_node_id=graph_node.id,
                              record_time=datetime.now())
    session.add(chosen_word)
    await session.flush()

    # update the "acquired", "mastery" fields in the GraphNode table
    # We have already checked if the word is in the GraphNode table.
    stmt = select(GraphNode).where(GraphNode.lemma == word.lemma, GraphNode.graph_id == graph.id)
    graph_node = (await session.execute(stmt)).scalar_one_or_none()
    if not graph_node:
        raise ValueError(
            f"GraphNode not found for user_id when updating the mastery score after chosen a word:"
            f" {user_id}, word id: {word.id}")
    logger.debug(f"GraphNode's mastery before updating for word {word.lemma}: {graph_node.mastery}")

    # TODO: we did not choose to spread activation for this scenario, should discuss if it is necessary.
    graph_node.mastery -= weight_adjustment_for_chosen_word  # 0.15 by default
    # make sure mastery is not less than 0
    if graph_node.mastery < 0:
        graph_node.mastery = 0
    logger.debug(f"GraphNode's mastery after updating for word {word.lemma}: {graph_node.mastery}")
    session.add(graph_node)
    await session.flush()

    await session.commit()

    #  [(word_id, marked_as_learned, lemma, translation,  sentence, record_time)]
    return (chosen_word.word_id, chosen_word.marked_as_learned, chosen_word.lemma, chosen_word.translation,
            chosen_word.sentence, chosen_word.record_time)
