# Description: Service for generating gap-filling exercises based on a user's graph.
import random
import time
from typing import Dict, Any, List

import networkx as nx
from networkx.exception import NetworkXNoPath
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import logger
from app.core.utils.nlp import get_nlp_en
from app.models import GapFillingTable
from app.models import GraphEdge
from app.models import Word, Line, Sentence, GraphNode
from app.schemas.responses import GapFillingResponse

nlp_en = get_nlp_en()


# def generate_prompt(self, row):
#     return f"""
#     Task: Create a multiple-choice gap-filling exercise based on the following context.
#
#     Context:
#     - Original Sentence: {row.sentence}
#     - Word to Replace: {row.clean_word}
#     - Translation: {row.translation}
#
#     Instructions:
#     1. Create a gap in the original sentence by replacing '{row.clean_word}' with '____'
#     2. Generate 3 plausible distractors that:
#        - Are the same part of speech as '{row.clean_word}'
#        - Make sense in the context of the sentence
#        - Are not the correct word
#     3. Randomize the order of options
#     4. Ensure the correct answer is included
#
#     Output Format:
#     - Gapped Sentence
#     - Translation Hint
#     - 4 Options (A, B, C, D) in JSON format
#     """
#
# def call_gemini_api(self, prompt):
#     # model = genai.GenerativeModel("gemini-1.5-flash")
#     # response = model.generate_content(prompt)
#     # translated_text = response.text.strip()
#     model = genai.GenerativeModel('gemini-pro')
#     response = model.generate_content(prompt)
#     return response.text


async def generate_gap_filling_exercises(user_id: int, graph_id: int, session: AsyncSession,
                                         exercise_number: int = 10) -> List[GapFillingResponse]:
    """
    Generate gap-filling exercises by randomly selecting nodes from the top candidates.

    Args:
        user_id (int): The user id.
        graph_id (int): The graph id of the user.
        session (AsyncSession): The database session.
        exercise_number (int): Number of exercises to generate. Defaults to 10.

    Returns:
        list: A list of GapFillingResponse objects.
    """
    start_time = time.time()

    top_candidates = await find_top_candidates(graph_id, session, exercise_number=exercise_number)
    chosen_nodes = random.sample(list(top_candidates.keys()), k=min(exercise_number, len(top_candidates)))

    # === Preload Word, Line, Sentence ===
    words_stmt = select(Word)
    words = (await session.execute(words_stmt)).scalars().all()
    word_id_to_word = {word.id: word for word in words}
    word_text_to_words = {}
    for word in words:
        word_text_to_words.setdefault(word.word, []).append(word)

    lines_stmt = select(Line)
    lines = (await session.execute(lines_stmt)).scalars().all()
    line_id_to_line = {line.id: line for line in lines}

    sentences_stmt = select(Sentence).where(Sentence.language == "en")
    sentences = (await session.execute(sentences_stmt)).scalars().all()
    sentence_id_to_sentence = {sentence.id: sentence for sentence in sentences}

    preload_data = {
        "word_id_to_word": word_id_to_word,
        "word_text_to_words": word_text_to_words,
        "line_id_to_line": line_id_to_line,
        "sentence_id_to_sentence": sentence_id_to_sentence,
    }
    # === End Preload ===

    exercises = []
    for node_id in chosen_nodes:
        node = top_candidates[node_id]
        # logger.debug(f"-------Chosen node: {top_candidates[node_id]['lemma']}， node_id: {node_id}")

        # todo：it should be the case that for one node, three sentences, not for each unique word_text, debug for this
        #  issue
        select_list = await create_masked_sentence(node, session, preload_data)
        distractors = await create_distractors(node, graph_id, session)

        gap_filling_entry = GapFillingTable(
            user_id=user_id,
            node_id=node_id,
            correct_answer_lemma=node["lemma"],
            select_list=select_list,
            distractors=distractors,
        )
        session.add(gap_filling_entry)
        await session.flush()

        exercise = GapFillingResponse(
            exercise_id=gap_filling_entry.id,
            user_id=user_id,
            node_id=node_id,
            correct_answer_lemma=node["lemma"],
            select_list=select_list,
            distractors=distractors, )
        exercises.append(exercise)

    await session.commit()
    logger.debug(f"========Exercises: {exercises}")
    end_time = time.time()
    duration = end_time - start_time
    logger.info(f"Generated {len(exercises)} exercises for user {user_id} in {duration:.2f} seconds.")

    return exercises


async def find_top_candidates(graph_id: int,
                              session: AsyncSession,
                              mastery_threshold: float = 0.8,
                              exercise_number: int = 1):  # TODO: exercise_number default value is 10, set to 1 for
    # testing
    """
    Finds the top candidate nodes closest to the graph's center with mastery below a threshold and not acquired.

    Args:
        graph_id (int): The graph ID of the user.
        session (AsyncSession): The database session.
        mastery_threshold (float): Mastery score threshold. Defaults to 0.8.
        exercise_number (int): Number of top nodes to consider as candidates. Defaults to 10.

    Returns:
        dict: A dictionary containing node data and their associated sentences.
    """
    closeness_centrality = await get_closeness_centrality(graph_id, session)

    # Fetch graph nodes and sentences
    stmt = select(GraphNode).where(GraphNode.graph_id == graph_id)
    nodes = (await session.execute(stmt)).scalars().all()

    node_data = {
        node.id: {
            "id": node.id,
            "graph_id": node.graph_id,
            "lemma": node.lemma,
            "mastery": node.mastery,
            "word_ids": node.word_ids,
            "acquired": node.acquired,
        }
        for node in nodes
    }

    # Filter nodes based on mastery threshold and acquired status

    eligible_nodes = [node_id for node_id, centrality in sorted(closeness_centrality.items(), key=lambda x: -x[1])
                      if node_data[node_id]["mastery"] < mastery_threshold and not node_data[node_id]["acquired"]
                      ][:exercise_number]

    logger.debug(f"---------\nEligible nodes: {eligible_nodes}")

    # Basing on eligible_nodes, return dictionary of node_data
    top_candidates_data = {}
    for node_id in eligible_nodes:
        top_candidates_data[node_id] = node_data[node_id]

    top_candidates_lemmas = [v["lemma"] for k, v in top_candidates_data.items()]
    logger.debug(f"---------\nTop candidates: {top_candidates_lemmas}")

    return top_candidates_data


async def get_closeness_centrality(graph_id: int, session: AsyncSession):
    """
    Computes the closeness centrality of nodes in a user's graph.

    Args:
        graph_id (int): The graph ID of the user.
        session (AsyncSession): The database session.

    Returns:
        dict: A dictionary of node IDs and their closeness centrality.
    """
    stmt = select(GraphNode).where(GraphNode.graph_id == graph_id)
    nodes = (await session.execute(stmt)).scalars().all()

    stmt = select(GraphEdge).where(GraphEdge.graph_id == graph_id)
    edges = (await session.execute(stmt)).scalars().all()

    network = nx.Graph()

    for node in nodes:
        network.add_node(node.id, mastery=node.mastery)

    for edge in edges:
        network.add_edge(edge.node1_id, edge.node2_id, weight=1 - edge.weight)

    closeness_centrality = nx.closeness_centrality(network, distance="weight")
    return closeness_centrality


async def create_masked_sentence(chosen_node: Dict[str, Any], session: AsyncSession, preload_data: Dict[str,
Any]) -> List[Dict[str, Any]]:
    """
    Create masked sentences for one chosen node by masking the words.
    For each node, we find the unique word_texts and then find all sentences containing that word.
    We then mask the word_text in each sentence.
    At the end, we mix all the masked sentences for the same node (with corresponding word_text) and return random three if there are three, otherwise, return all.

    Args:
        chosen_node (Dict[str, Any]): The chosen node data. It has two keys: "node_data" and "sent_text".
        session (AsyncSession): The database session.
        preload_data (Dict[str, Any]): Preloaded data
    Returns:
        select_list: A list with two dictionaries. Each dictionary contains two keys ""word_text" and
        "masked_sentences". word_text is the word_text in the sentence, masked_sentences is a list of masked sentences.
       
    """
    # Use the preloaded data and the globally loaded Spacy model
    global nlp_en
    word_id_to_word = preload_data["word_id_to_word"]
    word_text_to_words = preload_data["word_text_to_words"]
    line_id_to_line = preload_data["line_id_to_line"]
    sentence_id_to_sentence = preload_data["sentence_id_to_sentence"]

    word_texts = set()
    for word_id in chosen_node["word_ids"]:
        word = word_id_to_word.get(word_id)
        if word:
            word_texts.add(word.word)

    word_text_masked_sentence_dict = {}
    for word_text in word_texts:
        words = word_text_to_words.get(word_text, [])
        sentences = set()
        for word in words:
            line = line_id_to_line.get(word.line_id)
            if line:
                sentence = sentence_id_to_sentence.get(line.sentence_id)
                if sentence:
                    if word_text in sentence.sentence_text:
                        sentences.add(sentence.sentence_text)
                        # 特殊情况，当line-sentence是一对多的时候，直接用line的text，避免失去文本。
                        # todo：更深层次debug
                    elif word_text in line.line_text:
                        sentences.add(line.line_text)

        # Mask all the word_text occurrence in each sentence
        # TODO: we put sentence's texts into a list directly, but in the future, we should use sentence_id here to reduce the size of the data.
        masked_sentences = []
        for sentence_tor_line_text in sentences:
            doc = nlp_en(sentence_tor_line_text)
            masked_sentence = [
                "____" if token.text.strip().lower() == word_text.strip().lower() else token.text
                for token in doc
            ]
            masked_sentences.append(" ".join(masked_sentence))
        word_text_masked_sentence_dict[word_text] = masked_sentences

    word_text_num = len(word_text_masked_sentence_dict.keys())

    select_list = []
    if word_text_num == 1:
        d = {}
        word = list(word_text_masked_sentence_dict.keys())[0]
        sentences = word_text_masked_sentence_dict[word]
        d["word"] = word
        if len(sentences) <= 3:
            # We choose all the sentences
            d["sentences"] = sentences
            select_list.append(d)
            return select_list
        else:
            # We choose 3 random sentences
            d["word"] = word
            d["sentences"] = random.sample(sentences, 3)
            select_list.append(d)
            return select_list

    elif word_text_num == 2:
        select_list = []
        remaining_sentences = {}
        for word_text in word_text_masked_sentence_dict.keys():
            d = {}
            d["word"] = word_text
            # We shuffle the sentences for each word_text
            random.shuffle(word_text_masked_sentence_dict[word_text])
            # choose one sentence from all the sentences for each word_text, keep the remaining sentences,
            # and then choose one sentence randomly from the remaining sentences
            d['sentences'] = [word_text_masked_sentence_dict[word_text][0]]
            select_list.append(d)

            if len(word_text_masked_sentence_dict[word_text]) > 1:
                remaining_sentences[word_text] = word_text_masked_sentence_dict[word_text][1:]
        # Choose one sentence randomly from the remaining sentences
        random_word_text = random.choice(list(remaining_sentences.keys()))
        random_sentence = random.choice(remaining_sentences[random_word_text])
        for word_text in select_list:
            if word_text['word'] == random_word_text:
                word_text['sentences'].append(random_sentence)
        return select_list

    elif word_text_num == 3:
        # We shuffle the sentences for each word_text, choose one sentence for each word_text
        for word_text in word_text_masked_sentence_dict.keys():
            d = {"word": word_text}
            random.shuffle(word_text_masked_sentence_dict[word_text])
            d["sentences"] = [word_text_masked_sentence_dict[word_text][0]]
            select_list.append(d)
        return select_list

    else:
        # We shuffle all the word_texts, choose 3 out of them
        # For each word_text from these 3, shuffle the sentences, choose one sentence for each word_text
        word_texts = list(word_text_masked_sentence_dict.keys())
        random.shuffle(word_texts)
        for word_text in word_texts[:3]:
            d = {"word": word_text}
            random.shuffle(word_text_masked_sentence_dict[word_text])
            d["sentences"] = [word_text_masked_sentence_dict[word_text][0]]
            select_list.append(d)
        return select_list


async def create_distractors(chosen_node: Dict[str, Any], graph_id: int, session: AsyncSession,
                             num_distractors: int = 3) -> List[str]:
    """
    Generate distractors for a gap-filling exercise by finding nodes at increasing edge distances.
    
    Args:
        chosen_node (Dict[str, Any]): The node for which to generate distractors
        graph_id (int): The graph ID
        session (AsyncSession): Database session
        num_distractors (int): Number of distractors to generate (default: 3)
    
    Returns:
        List[str]: List of distractor lemmas
    """
    # Get the graph structure
    stmt = select(GraphNode).where(GraphNode.graph_id == graph_id)
    nodes = (await session.execute(stmt)).scalars().all()

    stmt = select(GraphEdge).where(GraphEdge.graph_id == graph_id)
    edges = (await session.execute(stmt)).scalars().all()

    # Create NetworkX graph
    G = nx.Graph()
    node_map = {}  # Map node IDs to their data
    for node in nodes:
        G.add_node(node.id)
        # TODO: consider the possibility of maintaining a pos pool for later distractor generation
        node_map[node.id] = {
            "lemma": node.lemma,
            "mastery": node.mastery,
            "acquired": node.acquired
        }

    for edge in edges:
        G.add_edge(edge.node1_id, edge.node2_id)

    target_node_id = chosen_node["id"]
    distractors = []
    current_distance = 2  # Start from distance 2 (skipping immediate neighbors)
    max_attempts = 5  # Limit the number of attempts to find a path

    attempts = 0
    while len(distractors) < num_distractors and attempts < max_attempts:
        try:
            # Get nodes at current distance
            nodes_at_distance = set()
            for node in G.nodes():
                if nx.shortest_path_length(G, target_node_id, node) == current_distance:
                    nodes_at_distance.add(node)

            # Sort nodes by mastery score (now also filtering out acquired nodes)
            candidate_nodes = [
                (node_id, node_map[node_id])
                for node_id in nodes_at_distance
                if node_map[node_id]["mastery"] < 0.8 and not node_map[node_id]["acquired"]
            ]
            candidate_nodes.sort(key=lambda x: x[1]["mastery"])

            # Add candidates to distractors
            needed = num_distractors - len(distractors)
            for _, node_data in candidate_nodes[:needed]:
                distractors.append(node_data["lemma"])

            if not nodes_at_distance or current_distance > len(G.nodes):
                # If we've exhausted connected nodes or can't find more,
                # fill remaining slots with random nodes from the graph
                remaining_needed = num_distractors - len(distractors)
                if remaining_needed > 0:
                    # Get all eligible nodes not already selected (now also filtering out acquired nodes)
                    all_eligible = [
                        node_map[node_id]["lemma"]
                        for node_id in G.nodes()
                        if node_map[node_id]["mastery"] < 0.8
                           and not node_map[node_id]["acquired"]  # Added acquired check
                           and node_map[node_id]["lemma"] not in distractors
                           and node_id != target_node_id
                    ]

                    # Add random selections
                    random_selections = random.sample(
                        all_eligible,
                        min(remaining_needed, len(all_eligible))
                    )
                    distractors.extend(random_selections)
                break

            current_distance += 1

        except NetworkXNoPath:
            # logger.warning(
            #     f"No path found between node {target_node_id} and some nodes at distance {current_distance}.")

            # Handle the case where no path is found
            # You might want to skip this distance or use a fallback strategy
            current_distance += 1
            attempts += 1

    # If after max_attempts no path is found, choose random nodes
    if attempts >= max_attempts and len(distractors) < num_distractors:
        remaining_needed = num_distractors - len(distractors)
        all_eligible = [
            node_map[node_id]["lemma"]
            for node_id in G.nodes()
            if node_map[node_id]["mastery"] < 0.8
               and not node_map[node_id]["acquired"]
               and node_map[node_id]["lemma"] not in distractors
               and node_id != target_node_id
        ]
        random_selections = random.sample(
            all_eligible,
            min(remaining_needed, len(all_eligible))
        )
        distractors.extend(random_selections)

    return distractors[:num_distractors]


# Example usage:
if __name__ == "__main__":
    lemma_1 = "project"
    word_text_masked_sentence_list_1 = [
        [
            "project",
            [
                "masked sentence 1", "masked sentence 2", "masked sentence 3"
            ]
        ],
        [
            "projecting",
            [
                "masked sentence 4", "masked sentence 5"
            ]
        ]
    ]

    lemma_2 = "apple"
    word_text_masked_sentence_list_2 = [
        [
            "apple",
            [
                "masked sentence 1", "masked sentence 2", "masked sentence 3"
            ]
        ],
    ]

    lemma_3 = "tree"
    word_text_masked_sentence_list_3 = [
        [
            "trees",
            [
                "masked sentence 1", "masked sentence 2"
            ]
        ],
    ]

    lemma_4 = "tree"
    word_text_masked_sentence_list_4 = [
        [
            "tuzi",
            [
                "masked sentence 1",
            ]
        ],
    ]

    lemma_5 = "project"
    word_text_masked_sentence_list_5 = [
        [
            "project",
            [
                "masked sentence 1", "masked sentence 2",
            ]
        ],
        [
            "projecting",
            [
                "masked sentence 3"
            ]
        ]
    ]
