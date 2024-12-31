from pathlib import Path
from typing import Dict, Optional

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.utils.pos_align import align_pos
from app.models import Sentence, WordContext
from app.models import Word, UserWordAssociation


async def all_subtitles_frequency(word: Word, video_id: str, session: AsyncSession, ) -> int:
    """Get the frequency of this word in the subtitle of a given video."""
    # Usingthe video_id to look up the sentences from sentence_model, then use sentence_id to look up for words in word_context table. Then compare the lemma and the pos, find all the matches, increase the frequency by 1 for each match, otherwise, do nothing.

    # Get the sentences from sentence_model
    stmt = select(Sentence).where(Sentence.video_id == video_id)
    sentences = (await session.execute(stmt)).scalars().all()
    match_count = 0
    for sentence in sentences:
        # Get the words from word_context
        stmt = select(WordContext).where(WordContext.sentence_id.in_(sentences))
        words = (await session.execute(stmt)).scalars().all()
        # Compare the lemma and the pos
        for word in words:
            if word.lemma == word.lemma and word.pos == word.pos:
                match_count += 1
    return match_count


def complexity(word: Word) -> float:
    """Get the complexity of the word."""
    freq_subtlexus = _load_freq_lookup()
    if word.lemma in freq_subtlexus:
        return 5 - freq_subtlexus[word.lemma]

    # Calculate the mean of the distribution of freq_subtlexus values
    if freq_subtlexus:  # Ensure freq_subtlexus is not empty
        mean_freq_subtlexus = sum(freq_subtlexus.values()) / len(freq_subtlexus)
        return 5 - mean_freq_subtlexus  # Complexity as 5 minus the mean frequency

    # Fallback if freq_subtlexus is unexpectedly empty
    return 2.5


def _load_freq_lookup() -> Dict[str, float]:
    freq = pd.read_csv("../../resources/subtlexus.csv")
    return {w: f for w, f in freq[["Word", "Lg10WF"]].to_numpy()}


def fetch_cefr_from_dataset(word: Word) -> Optional[str]:
    """
    Looks up the CEFR level for the word in the resources based on its text and POS.

    Args:
        word: Word

    Returns:
        Optional[str]: The CEFR level (e.g., A1, B1, C2) if found, otherwise None.
    """
    try:
        cefr_path = Path("../../resources/cefr_j.csv")
        cefr_data = pd.read_csv(cefr_path)
        # Check for the required columns
        if (
                "headword" not in cefr_data.columns
                or "pos" not in cefr_data.columns
                or "CEFR" not in cefr_data.columns
        ):
            raise ValueError(
                "The CEFR resources must contain 'headword', 'pos', and 'CEFR' columns."
            )

        # Filter resources for matching headword and POS
        record = cefr_data[
            (cefr_data["headword"].str.lower() == word.lemma.lower())
        ]
        # Get the mapping between pos tags of CEFR-J dataset and Spacy.
        mapping = align_pos()

        # Further filter records where word.pos.lower() exists in the corresponding POS mapping
        record = record[
            record["pos"].apply(lambda pos: word.pos in mapping.get(pos, []))
        ]

        # Return the CEFR level if a match is found
        if not record.empty:
            return record.iloc[0]["CEFR"]  # Return the first match's CEFR level
        else:
            return None
    except FileNotFoundError:
        raise FileNotFoundError(f"The file at path '{cefr_path}' was not found.")
    except Exception as e:
        raise RuntimeError(
            f"An error occurred while processing the CEFR resources: {e}"
        )


async def collect_words_for_vocabulary(user_id: str, session: AsyncSession):
    """
    Use the information of pos, exclude words that are not nouns, verbs or adjectives and that contain numbers.
    Collects all the unique word and pos_tag pairs for this user.
    
    Args:
        user_id: User ID
        session: SQLAlchemy async session
    """
    # Get all words associated with this user through UserWordAssociation
    stmt = select(Word).join(UserWordAssociation).where(UserWordAssociation.user_id == user_id)
    words = (await session.execute(stmt)).scalars().all()
    # Exclude words that are not nouns, verbs or adjectives and that contain numbers
    words = [word for word in words if
             word.pos in ["NOUN", "VERB", "ADJ"] and not any(char.isdigit() for char in word.word)]
    print(len(words))

    # Get the CEFR level for each word
    for word in words:
        word.cefr = fetch_cefr_from_dataset(word)

    # Get unique word-POS pairs
    word_pos_pairs = {(word.word, word.pos) for word in words}
    print(len(word_pos_pairs))
    return word_pos_pairs


if __name__ == "__main__":
    pass
