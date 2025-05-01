import logging
from typing import Dict, List, Tuple

from app.core.logger import logger
from app.core.utils.nlp import get_nlp_en, get_nlp_zh
from app.core.utils.word_candidate_filter import is_valid_candidate

logger = logging.getLogger(__name__)

NLP_EN = get_nlp_en()
NLP_ZH = get_nlp_zh()


def analyze_text(
        lines_dict: dict[int, str],
        language: str,
        cefr_lookup: dict,
        prevalence_lookup: dict,
) -> Tuple[List[Dict[str, List[int]]], List[Dict[str, str]]]:
    """
    Analyzes the text to map sentences and tokens to lines.

    Args:
        lines_dict: Dictionary where keys are unique line IDs and values are the text lines
        language: The language of the text (either "zh" or "en")
        cefr_lookup: {(lemma, pos): level}
        prevalence_lookup: {word: prevalence}

    Returns:
        - A collection of sentences where each sentence has: line_ids and sentence_text.
        - A collection of tokens where each token has: line_id, text, lemma, pos, cefr, and vector.
    """
    nlp = NLP_ZH if language == "zh" else NLP_EN
    # Different joining strategy for Chinese and English
    joined_text = "".join(lines_dict.values()) if language == "zh" else " ".join(lines_dict.values())
    doc = nlp(joined_text)

    sentence_collection = []
    token_collection = []

    # Convert dictionary values to list while keeping track of IDs
    line_ids = list(lines_dict.keys())
    lines = list(lines_dict.values())

    # Create a mapping of positions to line IDs
    position_to_line = {}
    current_pos = 0

    for i, line in enumerate(lines):
        line_length = len(line)
        for pos in range(current_pos, current_pos + line_length):
            position_to_line[pos] = line_ids[i]
        current_pos += line_length
        if language == "en" and i < len(lines) - 1:
            # Account for the space we added between lines
            current_pos += 1

    # Process sentences
    for sent in doc.sents:
        start_idx = sent.start_char
        end_idx = sent.end_char

        # Find all unique line IDs that this sentence spans
        sentence_line_ids = set()
        for pos in range(start_idx, end_idx):
            if pos < len(joined_text):  # Ensure we don't go past the end of text
                line_id = position_to_line.get(pos)
                if line_id is not None:
                    sentence_line_ids.add(line_id)

        sentence_collection.append({
            "line_ids": sorted(list(sentence_line_ids)),
            "sentence_text": sent.text.strip()
        })

    # # If use word embeddings from BERT MULTILINGUAL
    # model_name = "bert-base-multilingual-cased"
    # bert_tokenizer = BertTokenizerFast.from_pretrained(model_name)
    # model = BertModel.from_pretrained(model_name)
    #
    # words = [token.text for token in doc]  # Use spaCy tokens
    # tokens = bert_tokenizer(words, return_tensors="pt", is_split_into_words=True, padding=True, truncation=True)
    #
    # # Get BERT embeddings in one forward pass
    # with torch.no_grad():
    #     outputs = model(**tokens)
    # last_hidden_states = outputs.last_hidden_state
    #
    # word_ids = tokens.word_ids()
    # word_embeddings = {}

    # for idx, word in enumerate(words):
    #     token_indices = [i for i, wid in enumerate(word_ids) if wid == idx]
    #     if token_indices:
    #         # Average the embeddings for subwords
    #         word_embedding = last_hidden_states[0][token_indices].mean(dim=0)
    #         word_embeddings[word] = word_embedding.numpy()

    # Process tokens
    for token in doc:

        # For debugging
        if token.lemma in ("new, book, century, change, create, early, feel, human, idea, imagination, "
                           "include, know, large, mean, place, spread, start, thing, think, time, "
                           "use, work, big").split(", "):
            logger.info(f"!!!!!_____!!!!!!should be either a1 or a2: {cefr_dict[token.lemma]}")

        # Use pre-processing rules to decide if we keep this work or not.
        is_valid_word, cefr_level = is_valid_candidate(language, token.lemma_, token.pos_, token.text, cefr_lookup,
                                                       prevalence_lookup,
                                                       NLP_EN, NLP_ZH)
        if not is_valid_word:
            # logger.debug(
            #     f"[TOKEN FILTER] Token did not pass linguistic filter: lemma='{token.lemma_}', pos='{token.pos_}', text='{token.text}'")
            continue

        # Find the line ID for this token
        token_line_ids = set()
        for pos in range(token.idx, token.idx + len(token.text)):
            if pos < len(joined_text):  # Ensure we don't go past the end of text
                line_id = position_to_line.get(pos)
                if line_id is not None:
                    token_line_ids.add(line_id)

        # if embedding is not None:
        #     print("\n\n------:", embedding.tolist())

        for line_id in token_line_ids:
            token_collection.append({
                "line_id": line_id,
                "text": token.text,
                "lemma": token.lemma_.lower(),
                "pos": token.pos_,
                "cefr": cefr_level,
                "vector": token.vector.tolist() if token.has_vector else None
                # # If use word embeddings from BERT MULTILINGUAL
                # "vector": embedding[token.text] if embedding is not None else None
            })
            # logger.debug(
            #     f"[TOKEN ADD] Added token: lemma='{token.lemma_}', pos='{token.pos_}', cefr='{cefr_level}', line_id={line_id}"
            # )
    return sentence_collection, token_collection


if __name__ == "__main__":
    pass
