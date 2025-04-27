import pandas as pd

from app.core.config import ENGLISH_WORD_PREVALENCES_PATH


def load_prevalence(file_path: str = ENGLISH_WORD_PREVALENCES_PATH) -> dict:
    df = pd.read_excel(file_path, usecols=["Word", "Prevalence"])
    prevalence_lookup = {
        str(row["Word"]).lower(): row["Prevalence"]
        for _, row in df.iterrows()
        if pd.notnull(row["Word"])  # 只保留Word不是NaN的行
    }
    return prevalence_lookup


def get_prevalence(surface_form, lemma, prevalence_lookup):
    surface_form = surface_form.lower()
    lemma = lemma.lower()
    if surface_form in prevalence_lookup:
        return prevalence_lookup[surface_form]
    elif lemma in prevalence_lookup:
        return prevalence_lookup[lemma]
    else:
        return None


if __name__ == "__main__":
    # Example usage
    prevalence_lookup = load_prevalence()
    # word = "showbiz"
    # lemma = "showbiz"
    # prevalence = get_prevalence(word, lemma, prevalence_lookup)
    # print(f"Prevalence of '{word}' or its lemma '{lemma}': {prevalence}")
    #
    # word = "Stanza"
    # lemma = "stanza"
    # prevalence = get_prevalence(word, lemma, prevalence_lookup)
    # print(f"Prevalence of '{word}' or its lemma '{lemma}': {prevalence}")
    #
    # word = "Lecithin"
    # lemma = "lecithin"
    # prevalence = get_prevalence(word, lemma, prevalence_lookup)
    # print(f"Prevalence of '{word}' or its lemma '{lemma}': {prevalence}")
    #
    # word = "testimony"
    # lemma = "testimony"
    # prevalence = get_prevalence(word, lemma, prevalence_lookup)
    # print(f"Prevalence of '{word}' or its lemma '{lemma}': {prevalence}")
    #
    # word = "outsider"
    # lemma = "outsider"
    # prevalence = get_prevalence(word, lemma, prevalence_lookup)
    # print(f"Prevalence of '{word}' or its lemma '{lemma}': {prevalence}")
    #
    # word = "genocide"
    # lemma = "genocide"
    # prevalence = get_prevalence(word, lemma, prevalence_lookup)
    # print(f"Prevalence of '{word}' or its lemma '{lemma}': {prevalence}")
    #
    # word = "intimacies"
    # lemma = "intimacies"
    # prevalence = get_prevalence(word, lemma, prevalence_lookup)
    # print(f"Prevalence of '{word}' or its lemma '{lemma}': {prevalence}")
    #
    # word = "manifest"
    # lemma = "manifest"
    # prevalence = get_prevalence(word, lemma, prevalence_lookup)
    # print(f"Prevalence of '{word}' or its lemma '{lemma}': {prevalence}")

    word = "fuckers"
    lemma = "fucker"
    prevalence = get_prevalence(word, lemma, prevalence_lookup)
    print(f"Prevalence of '{word}' or its lemma '{lemma}': {prevalence}")
