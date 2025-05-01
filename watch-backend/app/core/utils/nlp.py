from functools import lru_cache

import spacy


@lru_cache(maxsize=1)
def get_nlp_en():
    return spacy.load("en_core_web_lg")


@lru_cache(maxsize=1)
def get_nlp_zh():
    return spacy.load("zh_core_web_lg")
