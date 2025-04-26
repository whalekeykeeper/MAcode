"""
This is a helper which allows us to align the POS tags in CEFR_J dataset with the POS tags in Spacy label scheme.
"""
from pathlib import Path

import pandas as pd

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
    map = {}
    # The keys are pos tags in CEFR_J dataset.
    # The values are corresponding pos tags in Spacy label Scheme for en_core_web_lg. Url:
    # https://spacy.io/models/en#en_core_web_lg.

    # ToDo: check again if the values are all correct
    # Infinitive
    map["infinitive-to"] = ["TO"]
    # Nouns
    map["noun"] = ["NN", "NNS", "NNP", "NNPS"]
    # Verbs
    map["verb"] = ["VB", "VBD", "VBG", "VBN", "VBP", "VBZ"]
    map["do-verb"] = [
        "VB",
        "VBD",
        "VBG",
        "VBN",
        "VBP",
        "VBZ",
    ]  # DO can fall into regular verbs
    map["have-verb"] = ["VB", "VBD", "VBG", "VBN", "VBP", "VBZ"]  # Same as verbs
    map["be-verb"] = [
        "VB",
        "VBD",
        "VBG",
        "VBN",
        "VBP",
        "VBZ",
    ]  # BE can also fall under verbs
    # Adjectives
    map["adjective"] = ["JJ", "JJR", "JJS"]
    # Adverbs
    map["adverb"] = ["RB", "RBR", "RBS", "WRB"]
    # Prepositions
    map["preposition"] = ["IN"]
    # Determiners
    map["determiner"] = ["DT", "PDT", "WDT"]
    # Pronouns
    map["pronoun"] = ["PRP", "PRP$", "WP", "WP$"]
    # Modal auxiliaries
    map["modal auxiliary"] = ["MD"]
    # Conjunctions
    map["conjunction"] = ["CC", "IN"]
    # Numbers
    map["number"] = ["CD", "LS"]
    # Interjections
    map["interjection"] = ["UH"]
    # Others (including punctuations and special cases like spaces)
    map["other"] = [
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

    return map


def detect_cefrj_level(lemma: str) -> str:
    """
    Detect the CEFR level of the given word (lemma).

    Args:
        lemma (str): The word to look up.

    Returns:
        str: The lowest CEFR level (e.g., A1, A2, etc.) or an empty string if no match is found.
    """
    default_cefr_path = (
            Path(__file__).parent.parent.parent / "resources/CEFR_combined_data.csv"
    )

    cefr_data = pd.read_csv(default_cefr_path)

    matching_rows = cefr_data[
        cefr_data["headword"].str.lower().str.strip() == lemma.lower().strip()
        ]

    if not matching_rows.empty:
        # The CEFR levels in priority order
        cefr_priority_order = ["A1", "A2", "B1", "B2"]

        # Get all unique CEFR levels for the matching entries
        cefr_levels = matching_rows["CEFR"].unique()

        # Return the first level in priority order that is found in the matches
        for level in cefr_priority_order:
            if level in cefr_levels:
                return level

    return ""  # Return an empty string if no match is found


if __name__ == "__main__":
    tag_spacy = read_tag_spacy()
    pos_cefrj = read_pos_cefrj()
    mapping = _align_tag()

    # Compare the values in pos_spacy and the values in mapping, expected to return True.
    print((set(tag_spacy) - set(sum(mapping.values(), [])) == set()))
    print(set(pos_cefrj) - set(mapping.keys()) == set())
    print()
    # # Choose to use token.pos_ or token.tag_.
    # for l in ("block, book, century, change, create, cause, early, feel, human, idea, imagination, "
    #           "include, know, large, mean, place, spread, start, thing, think, time, "
    #           "use, work, big").split(", "):
    #     print(l, detect_cefrj_level(l))
    #     print()
    for l in "accuse ".split(" "):
        print(l, detect_cefrj_level(l))
        print()
