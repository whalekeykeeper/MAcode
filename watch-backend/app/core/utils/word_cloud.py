import os

import matplotlib.pyplot as plt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from wordcloud import WordCloud

from app.core.logger import logger
from app.models import GraphNode


async def generate_word_cloud(graph_id: int, session: AsyncSession):
    """
    Generate a word cloud for nodes in a graph based on their mastery scores.

    Args:
        graph_id (int): The ID of the graph.
        session (AsyncSession): The database session.

    Returns:
        None: The function saves the word cloud image to a file.
    """
    min_mastery = 0.51
    max_mastery = 1

    logger.info(
        f"Generating word cloud for graph {graph_id} with mastery scores between {min_mastery} and {max_mastery}.")

    # Fetch nodes within the specified mastery score range
    stmt = select(GraphNode).where(
        GraphNode.graph_id == graph_id,
        GraphNode.mastery >= min_mastery,
        GraphNode.mastery <= max_mastery
    )
    nodes = (await session.execute(stmt)).scalars().all()

    # Prepare data for the word cloud
    word_frequencies = {node.lemma: node.mastery for node in nodes}
    logger.debug(f"Word frequencies: {word_frequencies}")

    # Generate the word cloud
    logger.info("Generating word cloud...")
    wordcloud = WordCloud(width=800, height=400, background_color='white').generate_from_frequencies(word_frequencies)

    # Display the word cloud using matplotlib
    plt.figure(figsize=(10, 5))
    plt.imshow(wordcloud, interpolation='bilinear')
    plt.axis('off')
    plt.title(f"Word Cloud for Mastery Scores between {min_mastery} and {max_mastery}")
    plt.show()

    # Define the directory and ensure it exists
    output_dir = os.path.join('static', 'images')
    os.makedirs(output_dir, exist_ok=True)

    # Save the word cloud to the specified directory
    output_path = os.path.join(output_dir, f"word_cloud_{graph_id}_{min_mastery}_{max_mastery}.png")
    wordcloud.to_file(output_path)
