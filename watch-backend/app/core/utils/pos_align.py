"""
This is a helper which manually aligns pos tags from Spacy with the pos in the CEFR_J database.
"""
from pathlib import Path

import pandas as pd
import spacy

POS_TAG_SPACY = "$, '', ,, -LRB-, -RRB-, ., :, ADD, AFX, CC, CD, DT, EX, FW, HYPH, IN, JJ, JJR, JJS, LS, MD, NFP, NN, NNP, NNPS, NNS, PDT, POS, PRP, PRP$, RB, RBR, RBS, RP, SYM, TO, UH, VB, VBD, VBG, VBN, VBP, VBZ, WDT, WP, WP$, WRB, XX, _SP, ``"


def read_pos_spacy() -> list:
    return POS_TAG_SPACY.split(", ")


def read_pos_cefrj() -> list:
    """
    ['adverb', 'determiner', 'noun', 'have-verb', 'verb', 'infinitive-to', 'be-verb', 'pronoun', 'conjunction', 'number', 'preposition', 'interjection', 'modal auxiliary', 'adjective', 'do-verb']
    """
    cefr_path = Path("./app/resources/CEFR_combined_data.csv")
    data = pd.read_csv(cefr_path)
    return list(set(data["pos"]))


def align_pos() -> dict:
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
    pos_spacy = read_pos_spacy()
    pos_cefrj = read_pos_cefrj()
    mapping = align_pos()
    # Compare the values in pos_spacy and the values in mapping
    print(set(pos_spacy) - set(sum(mapping.values(), [])))
    print(spacy.explain("IN"))
