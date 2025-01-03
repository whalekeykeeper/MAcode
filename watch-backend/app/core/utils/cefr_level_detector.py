"""
This is a helper which allows us to align the POS tags in CEFR_J dataset with the POS tags in Spacy label scheme.
"""
from pathlib import Path

import pandas as pd

from app.core.logger import logger

"""
Fine-grained part-of-speech. See: https://spacy.io/api/token#attributes
"""
TAG_SPACY_STRING = "$, '', ,, -LRB-, -RRB-, ., :, ADD, AFX, CC, CD, DT, EX, FW, HYPH, IN, JJ, JJR, JJS, LS, MD, NFP, NN, NNP, NNPS, NNS, PDT, POS, PRP, PRP$, RB, RBR, RBS, RP, SYM, TO, UH, VB, VBD, VBG, VBN, VBP, VBZ, WDT, WP, WP$, WRB, XX, _SP, ``"

TAG_SPACY = [
    "$",
    "''",
    ",",
    "-LRB-",
    "-RRB-",
    ".",
    ":",
    "ADD",
    "AFX",
    "CC",
    "CD",
    "DT",
    "EX",
    "FW",
    "HYPH",
    "IN",
    "JJ",
    "JJR",
    "JJS",
    "LS",
    "MD",
    "NFP",
    "NN",
    "NNP",
    "NNPS",
    "NNS",
    "PDT",
    "POS",
    "PRP",
    "PRP$",
    "RB",
    "RBR",
    "RBS",
    "RP",
    "SYM",
    "TO",
    "UH",
    "VB",
    "VBD",
    "VBG",
    "VBN",
    "VBP",
    "VBZ",
    "WDT",
    "WP",
    "WP$",
    "WRB",
    "XX",
    "_SP",
    "``",
]

"""
Coarse-grained part-of-speech from the Universal POS tag set. See https://universaldependencies.org/u/pos/
"""
POS_SPACY_UNIVERSAL = {
    "open class words": ["NOUN", "VERB", "ADJ", "ADV", "PROPN", "INTJ"],
    "closed class words": [
        "DET",
        "PRON",
        "ADP",
        "AUX",
        "CCONJ",
        "PART",
        "NUM",
        "SCONJ",
    ],
    "other": ["PUNCT", "SYM", "X"],
}

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
    "have-verb",
    "adverb",
    "number",
    "interjection",
    "modal auxiliary",
    "noun",
    "verb",
    "do-verb",
    "pronoun",
    "be-verb",
    "infinitive-to",
    "conjunction",
    "adjective",
    "determiner",
    "preposition",
]


def align_with_spacy_tag(pos: str) -> str:
    """
    Given a pos tag in Spacy token.tag_, return the corresponding pos tag in CEFR_J dataset.
    """
    m = _align_tag()
    for cefrj_pos, spacy_pos in m.items():
        if pos in spacy_pos:
            return cefrj_pos
    return ""


def align_with_spacy_pos(pos: str) -> str:
    """
    Maps a POS tag from SpaCy's universal POS tags to CEFR_J POS tags.

    Args:
        pos (str): The POS tag from SpaCy's universal POS tags.

    Returns:
        str: The corresponding POS tag in CEFR_J.
    """
    # Mapping SpaCy POS keys to CEFR_J POS tags
    spacy_to_cefrj_mapping = {
        "ADJ": "adjective",
        "ADV": "adverb",
        "NUM": "number",
        "INTJ": "interjection",
        "AUX": "modal auxiliary",
        "NOUN": "noun",
        "VERB": "verb",
        "PRON": "pronoun",
        "DET": "determiner",
        "ADP": "preposition",
        "CCONJ": "conjunction",
        "SCONJ": "conjunction",
        "PROPN": "noun",
        "PART": "infinitive-to",
        "SYM": "other",
        "PUNCT": "other",
        "X": "other",
    }

    # Map the POS key to CEFR_J POS tag, if not found, return "other" as default
    return spacy_to_cefrj_mapping.get(pos, "other")


def detect_cefrj_level(text: str, pos: str, pos_or_tag: str) -> str:
    """
    Give text and pos for a word, the pos comes from either token.pos_ or token.tag_ in spacy,
    return the corresponding CEFR_J level if a match is found, otherwise return "".
    """
    default_cefr_path = (
            Path(__file__).parent.parent.parent / "resources/CEFR_combined_data.csv"
    )
    
    cefr_data = pd.read_csv(default_cefr_path)

    aligned_pos = (
        align_with_spacy_tag(pos) if pos_or_tag == "tag" else align_with_spacy_pos(pos)
    )
    if aligned_pos:
        matching_row = cefr_data[
            (cefr_data["headword"].str.lower() == text.lower().strip())
            & (cefr_data["pos"] == aligned_pos)
            ]
        if not matching_row.empty:
            return matching_row.iloc[0]["CEFR"]

    logger.debug(
        f"Cannot find CEFR_J level for word {text} with pos {aligned_pos} in spacy token.{pos_or_tag}_."
    )
    return ""


def read_tag_spacy() -> list:
    return TAG_SPACY_STRING.split(", ")


def read_pos_cefrj() -> list:
    """
    ['adverb', 'determiner', 'noun', 'have-verb', 'verb', 'infinitive-to', 'be-verb', 'pronoun', 'conjunction', 'number', 'preposition', 'interjection', 'modal auxiliary', 'adjective', 'do-verb']
    """
    cefr_path = Path("../../../app/resources/CEFR_combined_data.csv")
    data = pd.read_csv(cefr_path)
    return list(set(data["pos"]))


def _align_tag() -> dict:
    mapping = {}
    # The keys are pos tags in CEFR_J dataset.
    # The values are corresponding pos tags in Spacy label Scheme for en_core_web_lg. Url:
    # https://spacy.io/models/en#en_core_web_lg.

    # ToDo: check again if the values are all correct
    # Infinitive
    mapping["infinitive-to"] = ["TO"]
    # Nouns
    mapping["noun"] = ["NN", "NNS", "NNP", "NNPS"]
    # Verbs
    mapping["verb"] = ["VB", "VBD", "VBG", "VBN", "VBP", "VBZ"]
    mapping["do-verb"] = [
        "VB",
        "VBD",
        "VBG",
        "VBN",
        "VBP",
        "VBZ",
    ]  # DO can fall into regular verbs
    mapping["have-verb"] = ["VB", "VBD", "VBG", "VBN", "VBP", "VBZ"]  # Same as verbs
    mapping["be-verb"] = [
        "VB",
        "VBD",
        "VBG",
        "VBN",
        "VBP",
        "VBZ",
    ]  # BE can also fall under verbs
    # Adjectives
    mapping["adjective"] = ["JJ", "JJR", "JJS"]
    # Adverbs
    mapping["adverb"] = ["RB", "RBR", "RBS", "WRB"]
    # Prepositions
    mapping["preposition"] = ["IN"]
    # Determiners
    mapping["determiner"] = ["DT", "PDT", "WDT"]
    # Pronouns
    mapping["pronoun"] = ["PRP", "PRP$", "WP", "WP$"]
    # Modal auxiliaries
    mapping["modal auxiliary"] = ["MD"]
    # Conjunctions
    mapping["conjunction"] = ["CC", "IN"]
    # Numbers
    mapping["number"] = ["CD", "LS"]
    # Interjections
    mapping["interjection"] = ["UH"]
    # Others (including punctuations and special cases like spaces)
    mapping["other"] = [
        "FW",
        "SYM",
        "XX",
        "NFP",
        "ADD",
        "$",
        "''",
        ",",
        "-LRB-",
        "-RRB-",
        ".",
        ":",
        "HYPH",
        "``",
        "_SP",
        "$",
        "AFX",
        "EX",
        "FW",
        "LS",
        "POS",
        "RP",
    ]

    return mapping


if __name__ == "__main__":
    tag_spacy = read_tag_spacy()
    pos_cefrj = read_pos_cefrj()
    mapping = _align_tag()

    # Compare the values in pos_spacy and the values in mapping, expected to return True.
    print((set(tag_spacy) - set(sum(mapping.values(), [])) == set()))
    print(set(pos_cefrj) - set(mapping.keys()) == set())
    print()
    # Choose to use token.pos_ or token.tag_.
    print(detect_cefrj_level("desk", "NOUN", "pos"))
    print(detect_cefrj_level("stressful", "ADJ", "pos"))

    print(detect_cefrj_level("move", "VB", "tag"))
