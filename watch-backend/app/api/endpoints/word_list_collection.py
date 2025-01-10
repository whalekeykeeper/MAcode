from fastapi import APIRouter

# word_list_collection.router, prefix="/word_list_collection", tags=["word_list_collection"]

"""
This file contains endpoints to show a collection of words as a table.
This table shows (checkbox, word, word_in_another_language_from_bilingual_subtitle, sentence) in a table with 4 columns.
The words are fetched from the database from the "chosen_words" table.
The order is from the least mastery score. If the mastery score is the same, the order is from the earliest chosen time.
The checkbox "acquired" is used to let the user eliminate the words from generating exercises manually.
"""

router = APIRouter()


@router.get("/")
def get_word_list():
    """
    A function to get the word list from the database
    """
    return db.query(ChosenWord).order_by(ChosenWord.mastery_score, ChosenWord.chosen_time).all()
