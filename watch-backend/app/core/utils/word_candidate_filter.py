# word_candidate_filter.py
import string

import spacy

"""
This script contains the filters for the word candidates.
It returns True if the word candidate passes the filters.
"""

NLP_ZH = spacy.load("zh_core_web_lg")
NLP_EN = spacy.load("en_core_web_lg")


def punctuation_filter_en(lemma):
    """
    This filter returns false if the token is a punctuation.
    """
    return not NLP_EN.vocab[str(lemma)].is_punct


def punctuation_filter_zh(lemma):
    """
    This filter returns false if the token is a punctuation.
    """
    return not NLP_ZH.vocab[str(lemma)].is_punct


def stopword_filter_en(lemma):
    """
    This filter returns false if the token belongs to stop word.
    """
    return not NLP_EN.vocab[str(lemma)].is_stop


def stopword_filter_zh(lemma):
    """
    This filter returns false if the token belongs to stop word
    """
    return not NLP_ZH.vocab[str(lemma)].is_stop


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


def filter_pipeline(language, lemma, pos, text):
    """
    This method filters out words based on their frequency in the corpus.
    """
    if language == 'en' and len(lemma) <= 2:
        return False

    # If the word contains punctuations or chars [0-9] return False
    if any(char in text for char in string.punctuation + string.digits):
        return False

    if language not in ['en', 'zh']:
        return False

    return punctuation_filter_en(lemma) and stopword_filter_en(lemma) and pos_filter(pos) and empty_string_filter(
        text)


if __name__ == "__main__":
    # Expected output: False
    print(punctuation_filter_en(","))
    print(punctuation_filter_zh("，"))
    print(stopword_filter_en("A"))
    print(stopword_filter_zh("的"))
    print(pos_filter("CCONJ"))
    print(cefr_filter("en", "cause"))
    print(cefr_filter("en", "use"))
    print(filter_pipeline('en', '14th', 'NOUN', '14th'))
    print(filter_pipeline("en", "big", "ADJ", "Big"))
    print(filter_pipeline("de", "the", "DET", "The"))
    print(filter_pipeline('en', 'apple\'', 'NOUN', 'apple\''))
    print(filter_pipeline('en', '张3', 'NOUN', '张3'))
    print()

    # Expected output: True
    print(punctuation_filter_en("apple"))
    print(punctuation_filter_zh("苹果"))
    print(stopword_filter_en("tree"))
    print(stopword_filter_zh("树"))
    print(pos_filter("VERB"))
    print(filter_pipeline("zh", "苹果", "NOUN", "apples"))  # made-up example
    print(filter_pipeline("zh", "苹果", "NOUN", "apples"))  # made-up example
