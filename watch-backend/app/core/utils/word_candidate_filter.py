# word_candidate_filter.py

import string
from typing import Tuple

from app.core.utils.cefr_level_detector import detect_cefr_level
from app.core.utils.cefr_level_detector import load_cefr_lookup
from app.core.utils.nlp import get_nlp_en, get_nlp_zh
from app.core.utils.prevalence_detector import get_prevalence
from app.core.utils.prevalence_detector import load_prevalence

"""
This script contains the filters for the word candidates.
It returns True if the word candidate passes the filters.
"""


def is_valid_candidate(language, lemma, pos, token_text, cefr_lookup, prevalence_lookup, nlp_en, nlp_zh) -> Tuple[bool,
str]:
    """
    This method for preprocessing for English.
    For any word, it checks if the word is a valid candidate.
    """
    lemma = lemma.strip().lower()
    token_text = token_text.strip().lower()
    if language == "en":
        has_valid_ling = _filter_by_linguistic_criteria(language, lemma, pos,
                                                        token_text, nlp_en)
        if not has_valid_ling:
            return False, ""  # To fail faster.

        has_valid_cefr, cefr = _filter_by_cefr_level(lemma, pos, cefr_lookup)
        if not has_valid_cefr:
            return False, ""

        has_valid_prevalence = _filter_by_prevalence(lemma, token_text, prevalence_lookup)
        # print(f"For lemma {lemma} with pos {pos}, CEFR: {cefr}, Valid Ling: {has_valid_ling}, Valid Prevalence:"
        #       f" {has_valid_prevalence}")
        if not has_valid_prevalence:
            return False, ""

        return True, cefr
    elif language == "zh":
        has_valid_ling = _filter_by_linguistic_criteria(language, lemma, pos,
                                                        token_text, nlp_zh)
        # print(f"For lemma {lemma} with pos {pos}, Valid Ling: {has_valid_ling}")
        return has_valid_ling, ""
    else:
        return False, "Chinese not supported"


def _filter_by_linguistic_criteria(language, lemma, pos, token_text, nlp_data):
    if language == "en" and len(lemma) <= 2:
        return False

    # If the word contains punctuations or chars [0-9] return False
    if any(char in token_text for char in string.punctuation + string.digits):
        return False

    if language == "zh":
        return (punctuation_filter_zh(lemma, nlp_data) and stopword_filter_zh(lemma, nlp_data) and pos_filter(pos) and
                empty_string_filter(token_text))

    elif language == "en":
        return (punctuation_filter_en(lemma, nlp_data) and stopword_filter_en(lemma, nlp_data) and pos_filter(pos) and
                empty_string_filter(token_text))
    else:
        return False


def _filter_by_cefr_level(lemma, pos, cefr_lookup) -> Tuple[bool, str]:
    cefr_level = detect_cefr_level(lemma, pos, cefr_lookup)
    if cefr_level not in ["A1", "A2", "B1"]:
        return True, cefr_level
    else:
        return False, ""


def _filter_by_prevalence(lemma, token_text, prevalence_lookup, prevalence_threshold=1.96) -> bool:
    """
    prevalence = 1.96 means 97.5% of the population knows the word.
    """
    prevalence_score = get_prevalence(token_text, lemma, prevalence_lookup)
    if prevalence_score is None:
        return True
    elif prevalence_score < prevalence_threshold:
        return True
    else:
        return False


def punctuation_filter_en(lemma, nlp_en):
    """
    This filter returns false if the token is a punctuation.
    """
    return not nlp_en.vocab[str(lemma)].is_punct


def punctuation_filter_zh(lemma, nlp_zh):
    """
    This filter returns false if the token is a punctuation.
    """
    return not nlp_zh.vocab[str(lemma)].is_punct


def stopword_filter_en(lemma, nlp_en):
    """
    This filter returns false if the token belongs to stop word.
    """
    return not nlp_en.vocab[str(lemma)].is_stop


def stopword_filter_zh(lemma, nlp_zh):
    """
    This filter returns false if the token belongs to stop word
    """
    return not nlp_zh.vocab[str(lemma)].is_stop


def pos_filter(pos):
    """
    This method filters out words based on their POS.
    """
    return pos in ["NOUN", "VERB", "ADJ", "ADV", "PROPN", "INTJ"]


def empty_string_filter(text):
    """
    This filter returns false if the token is an empty string.
    """
    return text != ""


if __name__ == "__main__":
    nlp_en = get_nlp_en()
    nlp_zh = get_nlp_zh()
    cefr_lookup = load_cefr_lookup()
    prevalence_lookup = load_prevalence()

    # # Example 1: Invalid English candidate (cefr level A1)
    # print(is_valid_candidate(
    #     language="en",
    #     lemma="apple",
    #     pos="NOUN",
    #     token_text="Apple",
    #     cefr_lookup=cefr_lookup,
    #     prevalence_lookup=prevalence_lookup,
    #     nlp_en=nlp_en,
    #     nlp_zh=nlp_zh
    # ))  # Expected: (False, “”)
    #
    # # Example 2: Invalid English candidate (high prevalence)
    # print(is_valid_candidate(
    #     language="en",
    #     lemma="testimony",
    #     pos="NOUN",
    #     token_text="Testimony",
    #     cefr_lookup=cefr_lookup,
    #     prevalence_lookup=prevalence_lookup,
    #     nlp_en=nlp_en,
    #     nlp_zh=nlp_zh
    # ))  # Expected: (False, "B2")
    #
    # # Example 3: Invalid English candidate (punctuation)
    # print(is_valid_candidate(
    #     language="en",
    #     lemma="，",
    #     pos="PUNCT",
    #     token_text="，",
    #     cefr_lookup=cefr_lookup,
    #     prevalence_lookup=prevalence_lookup,
    #     nlp_en=nlp_en,
    #     nlp_zh=nlp_zh
    # ))  # Expected: (False, "")
    #
    # # Example 4: Invalid Chinese candidate (punctuation)
    # print(is_valid_candidate(
    #     language="zh",
    #     lemma="，",
    #     pos="PUNCT",
    #     token_text="，",
    #     cefr_lookup=cefr_lookup,
    #     prevalence_lookup=prevalence_lookup,
    #     nlp_en=nlp_en,
    #     nlp_zh=nlp_zh
    # ))  # Expected: (False, "")
    #
    # # Example 5: Valid English candidate
    # print(is_valid_candidate(
    #     language="en",
    #     lemma="stanza",
    #     pos="NOUN",
    #     token_text="Stanza",
    #     cefr_lookup=cefr_lookup,
    #     prevalence_lookup=prevalence_lookup,
    #     nlp_en=nlp_en,
    #     nlp_zh=nlp_zh
    # ))  # Expected: (True, "B2")
    #
    # # Example 5: Valid English candidate
    # print(is_valid_candidate(
    #     language="en",
    #     lemma="lecithin",
    #     pos="NOUN",
    #     token_text="Lecithin",
    #     cefr_lookup=cefr_lookup,
    #     prevalence_lookup=prevalence_lookup,
    #     nlp_en=nlp_en,
    #     nlp_zh=nlp_zh
    # ))  # Expected: (True, "unknown")
    #
    # # Example 6: Valid Chinese candidate
    # print(is_valid_candidate(
    #     language="zh",
    #     lemma="苹果",
    #     pos="NOUN",
    #     token_text="苹果",
    #     cefr_lookup=cefr_lookup,
    #     prevalence_lookup=prevalence_lookup,
    #     nlp_en=nlp_en,
    #     nlp_zh=nlp_zh
    # ))  # Expected: (True, "Chinese not supported")

    print(is_valid_candidate(
        language="en",
        lemma="internalize",
        pos="VERB",
        token_text="internalizes",
        cefr_lookup=cefr_lookup,
        prevalence_lookup=prevalence_lookup,
        nlp_en=nlp_en,
        nlp_zh=nlp_zh
    ))  # Expected: (True, "Chinese not supported")
