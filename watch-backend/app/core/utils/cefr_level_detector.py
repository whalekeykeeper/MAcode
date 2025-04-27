"""
This is a helper which allows us to align the POS tags in CEFR_J dataset with the POS tags in Spacy label scheme.
"""
import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

#
# """
# Fine-grained part-of-speech. See: https://spacy.io/api/token#attributes
# """
# TAG_SPACY_STRING = "$, '', ,, -LRB-, -RRB-, ., :, ADD, AFX, CC, CD, DT, EX, FW, HYPH, IN, JJ, JJR, JJS, LS, MD, NFP, NN, NNP, NNPS, NNS, PDT, POS, PRP, PRP$, RB, RBR, RBS, RP, SYM, TO, UH, VB, VBD, VBG, VBN, VBP, VBZ, WDT, WP, WP$, WRB, XX, _SP, ``"
#
# TAG_SPACY = [
#     "$",
#     "''",
#     ",",
#     "-LRB-",
#     "-RRB-",
#     ".",
#     ":",
#     "ADD",
#     "AFX",
#     "CC",
#     "CD",
#     "DT",
#     "EX",
#     "FW",
#     "HYPH",
#     "IN",
#     "JJ",
#     "JJR",
#     "JJS",
#     "LS",
#     "MD",
#     "NFP",
#     "NN",
#     "NNP",
#     "NNPS",
#     "NNS",
#     "PDT",
#     "POS",
#     "PRP",
#     "PRP$",
#     "RB",
#     "RBR",
#     "RBS",
#     "RP",
#     "SYM",
#     "TO",
#     "UH",
#     "VB",
#     "VBD",
#     "VBG",
#     "VBN",
#     "VBP",
#     "VBZ",
#     "WDT",
#     "WP",
#     "WP$",
#     "WRB",
#     "XX",
#     "_SP",
#     "``",
# ]
#
# """
# Coarse-grained part-of-speech from the Universal POS tag set. See https://universaldependencies.org/u/pos/
# """
# POS_SPACY_UNIVERSAL = {
#     "open class words": ["NOUN", "VERB", "ADJ", "ADV", "PROPN", "INTJ"],
#     "closed class words": [
#         "DET",
#         "PRON",
#         "ADP",
#         "AUX",
#         "CCONJ",
#         "PART",
#         "NUM",
#         "SCONJ",
#     ],
#     "other": ["PUNCT", "SYM", "X"],
# }
#
#
# def align_with_spacy_tag(pos: str) -> str:
#     """
#     Given a pos tag in Spacy token.tag_, return the corresponding pos tag in CEFR_J dataset.
#     """
#     m = _align_tag()
#     for cefrj_pos, spacy_pos in m.items():
#         if pos in spacy_pos:
#             return cefrj_pos
#     return ""
#
#
# def align_with_spacy_pos(pos: str) -> str:
#     """
#     Maps a POS tag from SpaCy's universal POS tags to CEFR_J POS tags.
#
#     Args:
#         pos (str): The POS tag from SpaCy's universal POS tags.
#
#     Returns:
#         str: The corresponding POS tag in CEFR_J.
#     """
#     # Mapping SpaCy POS keys to CEFR_J POS tags
#     spacy_to_cefrj_mapping = {
#         "ADJ": "adjective",
#         "ADV": "adverb",
#         "NUM": "number",
#         "INTJ": "interjection",
#         "AUX": "modal auxiliary",
#         "NOUN": "noun",
#         "VERB": "verb",
#         "PRON": "pronoun",
#         "DET": "determiner",
#         "ADP": "preposition",
#         "CCONJ": "conjunction",
#         "SCONJ": "conjunction",
#         "PROPN": "noun",
#         "PART": "infinitive-to",
#         "SYM": "other",
#         "PUNCT": "other",
#         "X": "other",
#     }
#
#     # Map the POS key to CEFR_J POS tag, if not found, return "other" as default
#     return spacy_to_cefrj_mapping.get(pos, "other")
#
#
# def read_tag_spacy() -> list:
#     return TAG_SPACY_STRING.split(", ")
#
#
# def read_pos_cefrj() -> list:
#     """
#     ['adverb', 'determiner', 'noun', 'have-verb', 'verb', 'infinitive-to', 'be-verb', 'pronoun', 'conjunction', 'number', 'preposition', 'interjection', 'modal auxiliary', 'adjective', 'do-verb']
#     """
#     cefr_path = Path("../../../app/resources/CEFR_combined_data.csv")
#     data = pd.read_csv(cefr_path)
#     return list(set(data["pos"]))
#
#
# def _align_tag() -> dict:
#     map = {}
#     # The keys are pos tags in CEFR_J dataset.
#     # The values are corresponding pos tags in Spacy label Scheme for en_core_web_lg. Url:
#     # https://spacy.io/models/en#en_core_web_lg.
#
#     # ToDo: check again if the values are all correct
#     # Infinitive
#     map["infinitive-to"] = ["TO"]
#     # Nouns
#     map["noun"] = ["NN", "NNS", "NNP", "NNPS"]
#     # Verbs
#     map["verb"] = ["VB", "VBD", "VBG", "VBN", "VBP", "VBZ"]
#     map["do-verb"] = [
#         "VB",
#         "VBD",
#         "VBG",
#         "VBN",
#         "VBP",
#         "VBZ",
#     ]  # DO can fall into regular verbs
#     map["have-verb"] = ["VB", "VBD", "VBG", "VBN", "VBP", "VBZ"]  # Same as verbs
#     map["be-verb"] = [
#         "VB",
#         "VBD",
#         "VBG",
#         "VBN",
#         "VBP",
#         "VBZ",
#     ]  # BE can also fall under verbs
#     # Adjectives
#     map["adjective"] = ["JJ", "JJR", "JJS"]
#     # Adverbs
#     map["adverb"] = ["RB", "RBR", "RBS", "WRB"]
#     # Prepositions
#     map["preposition"] = ["IN"]
#     # Determiners
#     map["determiner"] = ["DT", "PDT", "WDT"]
#     # Pronouns
#     map["pronoun"] = ["PRP", "PRP$", "WP", "WP$"]
#     # Modal auxiliaries
#     map["modal auxiliary"] = ["MD"]
#     # Conjunctions
#     map["conjunction"] = ["CC", "IN"]
#     # Numbers
#     map["number"] = ["CD", "LS"]
#     # Interjections
#     map["interjection"] = ["UH"]
#     # Others (including punctuations and special cases like spaces)
#     map["other"] = [
#         "FW",
#         "SYM",
#         "XX",
#         "NFP",
#         "ADD",
#         "$",
#         "''",
#         ",",
#         "-LRB-",
#         "-RRB-",
#         ".",
#         ":",
#         "HYPH",
#         "``",
#         "_SP",
#         "$",
#         "AFX",
#         "EX",
#         "FW",
#         "LS",
#         "POS",
#         "RP",
#     ]
#
#     return map

POS_SPACY_UNIVERSAL_DESCRIPTION = {
    "ADJ": "adjective",
    "ADP": "adposition",
    "ADV": "adverb",
    "AUX": "auxiliary",
    "CCONJ": "coordinating conjunction",
    "DET": "determiner",
    "INTJ": "interjection",
    "NOUN": "noun",
    "NUM": "numeral",
    "PART": "particle",
    "PRON": "pronoun",
    "PROPN": "proper noun",
    "PUNCT": "punctuation",
    "SCONJ": "subordinating conjunction",
    "SYM": "symbol",
    "VERB": "verb",
    "X": "other",
}

"""
POS tags in CEFR_J dataset.
"""
POS_CEFRJ = [
    "adjective",
    "adverb",
    "be-verb",
    "conjunction",
    "determiner",
    "do-verb",
    "have-verb",
    "infinitive-to",
    "interjection",
    "modal auxiliary",
    "noun",
    "number",
    "preposition",
    "pronoun",
    "verb"
]

SPACY_TO_CEFRJ_POS = {
    "NOUN": "noun",
    "PROPN": "noun",
    "VERB": "verb",
    "AUX": "modal auxiliary",

    "ADJ": "adjective",
    "ADV": "adverb",

    "ADP": "preposition",
    "CCONJ": "conjunction",
    "SCONJ": "conjunction",

    "PRON": "pronoun",
    "DET": "determiner",

    "NUM": "number",

    "INTJ": "interjection",

    "PART": "infinitive-to",

    "PUNCT": "other",
    "SYM": "other",
    "X": "other",
    "SPACE": "other",
}


def map_spacy_pos_to_cefrj(spacy_pos: str) -> str:
    return SPACY_TO_CEFRJ_POS.get(spacy_pos.upper(), "other")


def load_cefr_lookup(csv_path: str = None) -> dict:
    if csv_path is None:
        csv_path = Path(__file__).parent.parent.parent / "resources/CEFR_combined_data.csv"
    cefr_data = pd.read_csv(csv_path)

    cefr_lookup = {}

    for _, row in cefr_data.iterrows():
        lemma = row['headword'].strip().lower()
        original_pos = row['pos'].strip().lower()
        cefr_level = row['CEFR'].strip().upper()

        if original_pos == "other":
            continue

        key = (lemma, original_pos)
        if key not in cefr_lookup:
            cefr_lookup[key] = cefr_level

    return cefr_lookup


def detect_cefr_level(lemma: str, spacy_pos: str, cefr_lookup: dict) -> str:
    """
    Detect the CEFR level for a given lemma and POS.
    Logs whether a match was found.

    Args:
        lemma (str): Lemma (base form) of the word
        spacy_pos (str): POS from SpaCy
        cefr_lookup (dict): Preloaded CEFR lookup dictionary

    Returns:
        str: CEFR level ("A1", "A2", "B1", "B2", etc.) or empty string if not found
    """
    lemma = lemma.lower().strip()
    mapped_pos = map_spacy_pos_to_cefrj(spacy_pos)  # still need mapping SpaCy POS -> CEFR_POS
    key = (lemma, mapped_pos.lower())
    # print(f"Checking key: {key}")
    return cefr_lookup.get(key, "unknown")


if __name__ == "__main__":
    d = {"apple": "NOUN", "outsider": "NOUN", "safe": "ADJ", "new": "ADJ"}
    for lemma, pos in d.items():
        cefr_level = detect_cefr_level(lemma.lower(), pos, load_cefr_lookup())
        print(cefr_level)
