#
# def analyze_text(text, nlp):
#     doc = nlp(text)
#     results = []
#
#     for token in doc:
#         # Get word embedding (vector). Some tokens might not have vectors in the small models
#         vector = (
#             token.vector if token.has_vector else nlp.zeros(96)
#         )  # 96 is the default vector size for small models
#
#         result = {
#             "text": token.text,
#             "lemma": token.lemma_,
#             "pos": token.pos_,
#             "vector_sample": vector[:3].tolist(),  # Show first 3 dimensions for brevity
#         }
#         results.append(result)
#
#     return results
#
#
# # Example sentences
# en_text = (
#     "Billions of people deal with a nail-biting habit at some point in their lives."
# )
# zh_text = "翻译人员: Maple Dilidili校对人员: Jacky He。成千上万的人在人生中某个阶段会养成咬指甲的习惯。很多人付出极大的努力想要戒掉这个习惯，采用像手指表面搓辣椒，整天戴着手套，将手浸入盐中，以及想象细菌爬遍手指等方法。"
#
# # Analyze English text
# print("English Text Analysis:")
# print("-" * 80)
# en_results = analyze_text(en_text, nlp_en)
# for result in en_results:
#     print(f"Token: {result['text']}")
#     print(f"Lemma: {result['lemma']}")
#     print(f"POS: {result['pos']}")
#     print(f"Vector sample: {result['vector_sample']}")
#     print()
#
# print("\nChinese Text Analysis:")
# print("-" * 80)
# zh_results = analyze_text(zh_text, nlp_zh)
# for result in zh_results:
#     print(f"Token: {result['text']}")
#     print(f"Lemma: {result['lemma']}")
#     print(f"POS: {result['pos']}")
#     print(f"Vector sample: {result['vector_sample']}")
#     print()


#
# # nlp_zh = get_nlp_zh()
# # doc = nlp_zh(zh_text)
# # for sent in doc.sents:
# #     print(sent.text)
# #     print([token.text for token in sent])
# #     print([token.pos_ for token in sent])
# #     print([token.dep_ for token in sent])
# #     print([token.head.text for token in sent])
# #     print()
# nlp_zh = get_nlp_zh()
# doc = nlp_zh(zh_text)
# for sent in doc.sents:
#     print(sent.text)
#     print([token.text for token in sent])
#     print([token.pos_ for token in sent])
#     print([token.dep_ for token in sent])
#     print([token.head.text for token in sent])
#     print()


# new task:
# sentences = ['翻译人员: Maple Dilidili校对人员: Jacky He。',
#              '成千上万的人在人生中某个阶段会养成咬指甲的习惯。',
#              '很多人付出极大的努力想要戒掉这个习惯，采用像手指表面搓辣椒，整天戴着手套，将手浸入盐中，以及想象细菌爬遍手指等方法。',
#              '虽然并非所有人都习惯咬指甲，但我们大多数人的确都有想要戒掉的习惯。',
#              '6号句子开始，6号句子结束。',
#              '7号句子开始，7号句子结束。',
#              '8号句子。',
#              '9号句子开始，9号句子结束。']

# lines = ['翻译人员: Maple Dilidili校对人员: Jacky He。',
#          '成千上万的人在人生中某个阶段会养成咬指甲的习惯。',
#          '很多人付出极大的努力想要戒掉这个习惯，',
#          '采用像手指表面搓辣椒，',
#          '整天戴着手套，将手浸入盐中，',
#          '以及想象细菌爬遍手指等方法。虽然并非所有人都习惯咬指甲，',
#          '但我们大多数人的确都有想要戒掉的习惯。',
#          '6号句子开始，',
#          '6号句子结束。7号句子开始，',
#          '7号句子结束。8号句子。9号句子开始，',
#          '9号句子结束。']

# Note: a line can be exact a sentence, part of a sentence, parts of two sentences, parts of two sentcens and one or
# multiple full sentences in between.

# expected output:
# sentence_to_line = [[1], [2], [3, 4, 5, 6], [6, 7], [8, 9], [9, 10], [10], [10, 11]]

# Idea: Enumerating sentences to get each sentence. For each sentence, concatenate the lines to get the sentence,
# use as less as lines as possible, and record it in sentence_to_line.


# def map_sentences_to_lines(sentences, lines):
# sentence_to_line = []
# all_text = ''.join(lines)
# current_pos = 0
#
# # For each sentence, find which lines contain it
# for sentence in sentences:
#     # Find where this sentence starts in the complete text
#     # 更新句子开始和结束的index
#     sentence_start = all_text.index(sentence, current_pos)
#     sentence_end = sentence_start + len(sentence)
#     # 更新current_pos，从而在下一个循环中，将此时的句末索引用作搜索的起点坐标。变相把all_text给cut小了。
#     current_pos = sentence_end
#
#     # Find which lines contain parts of this sentence
#     current_line_start = 0
#     sentence_lines = []
#
#     for i, line in enumerate(lines, 1):  # 1-based indexing
#         # 更新此时的line的结束index，其值为：当前的line的index加上line的长度。
#         current_line_end = current_line_start + len(line)
#
#         # Check if this line overlaps with the sentence
#         # 如果（当当前line的起点<句子的终点）并且（当前line的终点>句子的起点）：
#         if (current_line_start < sentence_end and
#                 current_line_end > sentence_start):
#             # 那么，把这个line给当前句子标记上
#             sentence_lines.append(i)
#
#         # 如果循环很多次，line已经超过了句子范畴，那么line的起点就会>句子终点，就不回更新sentence_lines
#         # 如果刚开始循环，
#         # 当前line的起点，更新
#         current_line_start = current_line_end
#     #
#     sentence_to_line.append(sentence_lines)
#
#
# return sentence_to_line

# Case 1: Line overlaps with sentence (condition TRUE)
# Sentence:   |-----------------|
# Line:          |--------|
# Position:   0  5        15    20
# current_line_start = 5  < sentence_end = 20    ✓ TRUE
# current_line_end = 15   > sentence_start = 0    ✓ TRUE
# RESULT: Line contains part of sentence, append line number
#
# Case 2: Line overlaps with sentence (condition TRUE)
# Sentence:      |-----------------|
# Line:     |--------|
# Position: 0   5     10           20
# current_line_start = 0  < sentence_end = 20    ✓ TRUE
# current_line_end = 10   > sentence_start = 5    ✓ TRUE
# RESULT: Line contains part of sentence, append line number
#
# Case 3: Line is completely inside sentence (condition TRUE)
# Sentence:   |----------------------|
# Line:          |--------|
# Position:   0  5        15        25
# current_line_start = 5  < sentence_end = 25    ✓ TRUE
# current_line_end = 15   > sentence_start = 0    ✓ TRUE
# RESULT: Line contains part of sentence, append line number
#
# Case 4: Sentence is completely inside line (condition TRUE)
# Sentence:      |--------|
# Line:     |----------------------|
# Position: 0    5        15       25
# current_line_start = 0  < sentence_end = 15    ✓ TRUE
# current_line_end = 25   > sentence_start = 5    ✓ TRUE
# RESULT: Line contains part of sentence, append line number
#
# Case 5: No overlap - Line before sentence (condition FALSE)
# Sentence:              |--------|
# Line:     |--------|
# Position: 0        10  15       25
# current_line_start = 0  < sentence_end = 25    ✓ TRUE
# current_line_end = 10   > sentence_start = 15   ✗ FALSE
# RESULT: Line does not contain sentence, skip this line
#
# Case 6: No overlap - Line after sentence (condition FALSE)
# Sentence:   |--------|
# Line:                    |--------|
# Position:   0        10  15       25
# current_line_start = 15 < sentence_end = 10    ✗ FALSE
# current_line_end = 25   > sentence_start = 0    ✓ TRUE
# RESULT: Line does not contain sentence, skip this line

# Test the function

from nlp import get_nlp_en, get_nlp_zh

# Load English and Chinese models
nlp_en = get_nlp_en()
nlp_zh = get_nlp_zh()


def map_sentences_to_lines(sentences, lines_dict):
    """
    Maps each sentence to the line IDs that contain it.

    Args:
        sentences: List of complete sentences
        lines_dict: Dictionary where keys are unique line IDs and values are the text lines

    Returns:
        List of lists where each inner list contains the line IDs
        that make up the corresponding sentence
    """
    sentence_to_line = []
    # Convert dictionary values to list while keeping track of IDs
    line_ids = list(lines_dict.keys())
    lines = list(lines_dict.values())

    all_text = "".join(lines)
    current_pos = 0

    # For each sentence, find which lines contain it
    for sentence in sentences:
        # Find where this sentence starts in the complete text
        sentence_start = all_text.index(sentence, current_pos)
        sentence_end = sentence_start + len(sentence)
        current_pos = sentence_end

        # Find which lines contain parts of this sentence
        current_line_start = 0
        sentence_lines = []

        for i, line in enumerate(lines):
            current_line_end = current_line_start + len(line)

            # Check if this line overlaps with the sentence
            if current_line_start < sentence_end and current_line_end > sentence_start:
                sentence_lines.append(
                    line_ids[i]
                )  # Append the line ID instead of index

            current_line_start = current_line_end

        sentence_to_line.append(sentence_lines)

    return sentence_to_line


if __name__ == "__main__":
    # lines_dict = {
    #     1: "翻译人员: Maple。",
    #     2: "他喜欢旅行。",
    #     3: "他去过很多地方，",
    #     4: "比如a，",
    #     5: "比如b，",
    #     6: "比如c。虽然他很多假期，",
    #     7: "但永远不够。",
    #     8: "他想去日本，",
    #     9: "今年冬天。他想吃寿司，",
    #     10: "和去漫展。一年有四个季节。他说，",
    #     11: "要多去几次。",
    #     12: "真好。",
    # }

    # doc = nlp_zh("".join(lines_dict.values()))
    # sentences = []
    # for sent in doc.sents:
    #     print(sent.text)
    #     print([token.text for token in sent])
    #     print()
    #     sentences.append(sent.text)

    # result = map_sentences_to_lines(sentences, lines_dict)
    # print(
    #     result
    # )  # expected: [[1], [2], [3, 4, 5, 6], [6, 7], [8, 9], [9, 10], [10], [10, 11], [12]]

    # import webvtt
    # from pathlib import Path
    #
    # vtt_path = Path(__file__).parent.parent.parent.parent / "static" / "3RxBIu-cd_Y" / "3RxBIu-cd_Y_bilingual.vtt"
    # print(vtt_path)
    # for caption in webvtt.read(str(vtt_path)):
    #     # print(caption.start)  # cue start time
    #     # print(caption.end)  # cue end time
    #     # print(caption.text)  # cue payload
    #     # print(caption.voice)
    #     print(type(caption.end))
    #     if caption.end == "00:00:07.000":
    #         print("Yeah!!!")
    #     break

    from spacy.lang.zh import Chinese

    NLP_EN = get_nlp_en()
    NLP_ZH = get_nlp_zh()
    # print(NLP_EN.tokenizer.rules)  # Get English tokenizer rules
    # print(NLP_ZH.tokenizer.rules)  # Get Chinese tokenizer rules
    text = "这是一段简体中文。需要进行分词。南京市长江大桥发表了讲话。他在北京大学学习画画。"
    language = "zh"

    nlp = NLP_ZH if language == "zh" else NLP_EN
    print(nlp.tokenizer.__class__)
    doc = nlp(text)
    print([token.text for token in doc])

    print("---------------")
    cfg = {"segmenter": "pkuseg"}
    nlp = Chinese.from_config({"nlp": {"tokenizer": cfg}})
    print(nlp.tokenizer.__class__)
    nlp.tokenizer.initialize(pkuseg_model="mixed")
    doc = nlp(text)
    print([token.text for token in doc])

    print("---------------")
    cfg = {"segmenter": "jieba"}
    nlp = Chinese.from_config({"nlp": {"tokenizer": cfg}})
    print(nlp.tokenizer.__class__)
    doc = nlp(text)
    print([token.text for token in doc])

    print("---------------")
    nlp = Chinese()
    doc = nlp(text)
    print([token.text for token in doc])

    print("---------------")

    text = "Dr. John Doe is a professor at the University of California, Berkeley."
    language = "en"
    nlp = NLP_ZH if language == "zh" else NLP_EN
    print(nlp.tokenizer.__class__)
    doc = nlp(text)
    print([token.text for token in doc])
