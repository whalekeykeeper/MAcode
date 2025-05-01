from typing import Dict, List, Tuple

from nlp import get_nlp_en, get_nlp_zh

# Load English and Chinese models
nlp_en = get_nlp_en()
nlp_zh = get_nlp_zh()


# def analyze_text(lines_dict):
#     """
#     Analyzes the text to map sentences and tokens to lines.
#
#     Args:
#         lines_dict: Dictionary where keys are unique line IDs and values are the text lines
#
#     Returns:
#         - A collection of sentences where each sentence has:
#           line_ids and sentence_text.
#         - A collection of tokens where each token has:
#           line_id, text, lemma, and pos.
#     """
#     doc = nlp_zh("".join(lines_dict.values()))
#     sentence_collection = []
#     token_collection = []
#
#     # Convert dictionary values to list while keeping track of IDs
#     line_ids = list(lines_dict.keys())
#     lines = list(lines_dict.values())
#
#     all_text = "".join(lines)
#     current_pos = 0
#
#     # Map sentences to lines
#     for sentence_id, sent in enumerate(doc.sents, start=1):
#         sentence = sent.text
#         sentence_start = all_text.index(sentence, current_pos)
#         sentence_end = sentence_start + len(sentence)
#         current_pos = sentence_end
#
#         current_line_start = 0
#         sentence_lines = []
#
#         for i, line in enumerate(lines):
#             current_line_end = current_line_start + len(line)
#
#             # Check if this line overlaps with the sentence
#             if current_line_start < sentence_end and current_line_end > sentence_start:
#                 sentence_lines.append(line_ids[i])  # Append the line ID
#
#             current_line_start = current_line_end
#
#         sentence_collection.append(
#             {"line_ids": sentence_lines, "sentence_text": sentence}
#         )
#
#     # Map tokens to lines
#     current_line_start = 0
#     for i, line in enumerate(lines):
#         current_line_end = current_line_start + len(line)
#         line_id = line_ids[i]
#
#         # Find tokens within this line
#         for token in doc:
#             token_start = token.idx
#             token_end = token_start + len(token.text)
#
#             if (
#                     current_line_start <= token_start < current_line_end
#                     or current_line_start < token_end <= current_line_end
#                     or (token_start < current_line_start and token_end > current_line_end)
#             ):
#                 token_collection.append(
#                     {
#                         "line_id": line_id,
#                         "text": token.text,
#                         "lemma": token.lemma_,
#                         "pos": token.pos_,
#                     }
#                 )
#
#         current_line_start = current_line_end
#
#     return sentence_collection, token_collection
#
#


def analyze_text_2(
        lines_dict: dict[int, str], language: str
) -> Tuple[List[Dict[str, List[int]]], List[Dict[str, str]]]:
    """
    Analyzes the text to map sentences and tokens to lines.

    Args:
        lines_dict: Dictionary where keys are unique line IDs and values are the text lines
        language: The language of the text (either "zh" or "en")

    Returns:
        - A collection of sentences where each sentence has:
          line_ids and sentence_text.
        - A collection of tokens where each token has:
          line_id, text, lemma, and pos.
    """
    nlp_en = get_nlp_en()
    nlp_zh = get_nlp_zh()
    nlp = nlp_zh if language == "zh" else nlp_en

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

    # Process tokens
    for token in doc:
        start_idx = token.idx
        end_idx = start_idx + len(token.text)

        # Find the line ID for this token
        token_line_ids = set()
        for pos in range(start_idx, end_idx):
            if pos < len(joined_text):  # Ensure we don't go past the end of text
                line_id = position_to_line.get(pos)
                if line_id is not None:
                    token_line_ids.add(line_id)

        for line_id in token_line_ids:
            token_collection.append({
                "line_id": line_id,
                "text": token.text,
                "lemma": token.lemma_,
                "pos": token.pos_
            })

    return sentence_collection, token_collection


if __name__ == "__main__":
    lines_zh = {
        1: "翻译人员: Maple。",
        2: "他喜欢旅行。",
        3: "他去过很多地方，",
        4: "比如a，",
        5: "比如b，",
        6: "比如c。虽然他很多假期，",
        7: "但永远不够。",
        8: "他想去日本，",
        9: "今年冬天。他想吃寿司，",
        10: "和去漫展。一年有四个季节。他说，",
        11: "要多去几次。",
        12: "真好。",
    }
    lines_en = {
        16: "So what's the best way to break one?",
        18: 'Scientists define habits as behaviors that are performed regularly,',
        20: 'and cued subconsciously in response to certain environments,',
        22: 'whether it be a location, time of day, or even an emotional state.',
        24: 'They can include simple actions like picking your hair when stressed,',
        26: 'but also more complex practices ingrained in daily routines,',
        28: 'like staying up late or brewing your coffee in the morning.'}

    for l, lan in [(lines_en, "en"), (lines_zh, "zh")]:
        sentence_collection, token_collection = analyze_text_2(l, lan)

        print(f"Sentence Collection for language {lan}:")
        sentences = []
        for sentence in sentence_collection:
            sentences.append(sentence.get("sentence_text"))
            print(sentence.get("sentence_text"))
            print("\n")

        # print("\nToken Collection:")
        # for token in token_collection:
        #     print(token)

"""
    # Current output for sentences:
    sentences = [
        "So what's the best way to break one?Scientists define habits as behaviors that are performed regularly,and cued subconsciously in response to certain environments,whether it be a location, time of day, or even an emotional state.",
        "They can include simple actions like picking your hair when stressed,but also more complex practices ingrained in daily routines,like staying up late or brewing your coffee in the morning."]
    # Expected output for sentences:
    expected_sentences = [
        "So what's the best way to break one?",
        "Scientists define habits as behaviors that are performed regularly, and cued subconsciously in response to certain environments, whether it be a location, time of day, or even an emotional state.",
        "They can include simple actions like picking your hair when stressed, but also more complex practices ingrained in daily routines, like staying up late or brewing your coffee in the morning.",
    ]
"""
