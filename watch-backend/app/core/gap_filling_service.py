# Description: Service for generating gap-filling exercises based on a user's graph.
from sqlalchemy.ext.asyncio import AsyncSession

MOCK_OPTIONS = ["option1", "option2", "option3"]


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
#
async def generate_gap_filling_exercises(user_id: int, session: AsyncSession, exercise_number: int = 10):
    """
    Generate gap-filling exercises by randomly selecting nodes from the top candidates.

    Args:
        user_id (int): The ID of the user.
        session (AsyncSession): The database session.
        exercise_number (int): Number of exercises to generate. Defaults to 10.

    Returns:
        list: A list of exercises with node data and masked sentences.
    """
    top_candidates = await find_top_candidates(user_id, session, exercise_number=exercise_number)
    chosen_nodes = random.sample(list(top_candidates.keys()), k=min(exercise_number, len(top_candidates)))

    exercises = []
    for node_id in chosen_nodes:
        chosen_node = top_candidates[node_id]
        masked_sentences = create_masked_sentence(chosen_node)
        distractors = create_distractors(chosen_node, masked_sentences)
        exercises.append({
            "node_data": chosen_node["node_data"],
            "masked_sentences": masked_sentences,
            "distractors": distractors
        })

    return exercises


async def find_top_candidates(user_id: int,
                              session: AsyncSession,
                              mastery_threshold: float = 0.8,
                              exercise_number: int = 10):
    """
    Finds the top candidate nodes closest to the graph's center with mastery below a threshold and not acquired.

    Args:
        user_id (int): The ID of the user.
        session (AsyncSession): The database session.
        mastery_threshold (float): Mastery score threshold. Defaults to 0.8.
        exercise_number (int): Number of top nodes to consider as candidates. Defaults to 10.

    Returns:
        dict: A dictionary containing node data and their associated sentences.
    """
    closeness_centrality = await get_closeness_centrality(user_id, session)

    # Fetch graph nodes and sentences
    stmt = select(GraphNode).where(GraphNode.graph_id == user_id)
    nodes = (await session.execute(stmt)).scalars().all()

    node_data = {
        node.id: {
            "lemma": node.lemma,
            "mastery": node.mastery,
            "word_ids": node.word_ids,
            "acquired": node.acquired,
        }
        for node in nodes
    }

    # Filter nodes based on mastery threshold and acquired status
    eligible_nodes = [
                         node_id
                         for node_id, centrality in sorted(closeness_centrality.items(), key=lambda x: -x[1])
                         if node_data[node_id]["mastery"] < mastery_threshold and not node_data[node_id]["acquired"]
                     ][:exercise_number]

    # Fetch sentences associated with the top nodes
    top_candidates_data = {}
    for node_id in eligible_nodes:
        word_ids = node_data[node_id]["word_ids"]
        stmt = select(Sentence).where(Sentence.line_ids.contains(word_ids))
        sentences = (await session.execute(stmt)).scalars().all()
        top_candidates_data[node_id] = {
            "node_data": node_data[node_id],
            "sentences": [sentence.sentence_text for sentence in sentences]
        }

    return top_candidates_data


async def get_closeness_centrality(user_id: int, session: AsyncSession):
    """
    Computes the closeness centrality of nodes in a user's graph.

    Args:
        user_id (int): The ID of the user.
        session (AsyncSession): The database session.

    Returns:
        dict: A dictionary of node IDs and their closeness centrality.
    """
    stmt = select(Graph).where(Graph.user_id == user_id)
    graph_entry = (await session.execute(stmt)).scalar_one_or_none()

    if not graph_entry:
        raise ValueError(f"No graph found for user ID {user_id}.")

    stmt = select(GraphNode).where(GraphNode.graph_id == graph_entry.id)
    nodes = (await session.execute(stmt)).scalars().all()

    stmt = select(GraphEdge).where(GraphEdge.graph_id == graph_entry.id)
    edges = (await session.execute(stmt)).scalars().all()

    network = nx.Graph()

    for node in nodes:
        network.add_node(node.id, mastery=node.mastery)

    for edge in edges:
        network.add_edge(edge.node1_id, edge.node2_id, weight=1 - edge.weight)

    closeness_centrality = nx.closeness_centrality(network, distance="weight")
    return closeness_centrality


def create_masked_sentence(chosen_node):
    """
    Create masked sentences for a chosen node by masking the words corresponding to its word IDs.

    Args:
        chosen_node (dict): The data of the chosen node.

    Returns:
        list: A list of masked sentences.
    """
    sentences = chosen_node["sentences"]
    word_ids = set(chosen_node["node_data"]["word_ids"])

    # TODO: If a sentence has multiple occurrences of the same word, mask only the first occurrence.
    masked_sentences = []
    for sentence in sentences[:3]:
        words = sentence.split()
        masked_sentence = " ".join(
            ["_____" if str(word_id) in word_ids else word for word_id, word in enumerate(words)])
        masked_sentences.append(masked_sentence)

    return masked_sentences


def create_distractors(chosen_node, masked_sentences):
    # TODO: Implement distractor generation based on the node's part of speech and context.
    return [MOCK_OPTIONS for _ in masked_sentences]


def save_exercise():
    pass


def fetch_gap_filling_exercises(user_id: int, session: AsyncSession):
    pass


def update_exercise_correctness(user_id: int, session: AsyncSession):
    pass
