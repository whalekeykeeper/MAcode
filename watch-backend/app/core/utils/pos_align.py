"""
This is a helper which manually aligns pos tags from Spacy with the pos in the CEFR_J database.
"""
import pandas as pd

POS_TAG_SPACY = "$, '', ,, -LRB-, -RRB-, ., :, ADD, AFX, CC, CD, DT, EX, FW, HYPH, IN, JJ, JJR, JJS, LS, MD, NFP, NN, NNP, NNPS, NNS, PDT, POS, PRP, PRP$, RB, RBR, RBS, RP, SYM, TO, UH, VB, VBD, VBG, VBN, VBP, VBZ, WDT, WP, WP$, WRB, XX, _SP, ``"

def read_pos_spacy() -> list:
    return POS_TAG_SPACY.split(", ")

def read_pos_cefrj() -> list:
    data = pd.read_csv("../../resources/CEFR_combined_data.csv")
    return list(set(data['pos']))

def align_pos() -> dict:
    mapping = {}
    # The keys are pos tags in CEFR_J dataset.
    # The values are corresponding pos tags in Spacy label Scheme for en_core_web_lg. Url:
    # https://spacy.io/models/en#en_core_web_lg.
    mapping["interjection"] = ["UH"]
    mapping["adjective"] = ["JJ", "JJR", "JJS"]
    mapping["preposition"] = ["IN"]
    mapping["verb"] = ["VB", "VBD", "VBG", "VBN", "VBP", "VBZ"]
    mapping["conjunction"] = ["CC", "IN"]
    mapping["number"] = ["CD"]
    mapping["infinitive-to"] = ["TO"]
    mapping["determiner"] = ["DT", "PDT", "WDT"]
    mapping["modal auxiliary"] = ["MD"]
    mapping["pronoun"] = ["PRP", "PRP$", "WP", "WP$"]
    mapping["do-verb"] = ["VB", "VBD", "VBG", "VBN", "VBP", "VBZ"]
    mapping["have-verb"] = ["VB", "VBD", "VBG", "VBN", "VBP", "VBZ"]
    mapping["be-verb"] = ["VB", "VBD", "VBG", "VBN", "VBP", "VBZ"]
    mapping["adverb"] = ["RB", "RBR", "RBS", "RP", "WRB"]
    mapping["noun"] = ["NN", "NNS", "NNP", "NNPS"]
    mapping["other"] = ['$', "''", ',', '-LRB-', '-RRB-', '.', ':', 'ADD', 'AFX', 'EX', 'FW', 'HYPH', 'LS', 'NFP',
                        'POS', 'SYM', 'XX', '_SP', '``']
    return mapping

if __name__ == "__main__":
    pos_spacy = read_pos_spacy()
    pos_cefrj = read_pos_cefrj()
    mapping = align_pos()