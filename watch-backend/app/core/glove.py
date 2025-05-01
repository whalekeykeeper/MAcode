from pathlib import Path
from typing import Any, Dict

import numpy as np

from utils.nlp import get_nlp_en

# Load SpaCy models for English and Chinese
nlp_en = get_nlp_en()


# Load GloVe embeddings
def load_glove_embeddings(file_path: str) -> Dict[str, np.ndarray]:
    embeddings: Dict[str, np.ndarray] = {}
    with open(file_path, encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            values = line.split()
            try:
                word = values[0]
                vector = np.array(values[1:], dtype="float32")
                embeddings[word] = vector
            except ValueError as e:
                print(f"Skipping line {line_number} due to parsing error: {e}")
    return embeddings


# Retrieve word embedding for a given word
def get_word_embedding(word: str, embeddings: Dict[str, np.ndarray], embedding_dim: int = 300) -> np.ndarray:
    return embeddings.get(word, np.zeros(embedding_dim))


# Tokenize text and get embeddings
def get_embeddings_for_text(
        text: str,
        nlp_model: Any,
        embeddings: Dict[str, np.ndarray],
        embedding_dim: int = 300) -> Dict[str, np.ndarray]:
    doc = nlp_model(text)
    word_embeddings: Dict[str, np.ndarray] = {}
    for token in doc:
        if token.text.strip():  # Ignore empty or whitespace tokens
            embedding = get_word_embedding(token.text, embeddings, embedding_dim)
            word_embeddings[token.text] = embedding
    return word_embeddings


# Example usage
if __name__ == "__main__":
    glove_file = Path(__file__).parent.parent.parent / "app/resources/glove.840B.300d.txt"
    glove_embeddings: Dict[str, np.ndarray] = load_glove_embeddings(glove_file)

    english_text = "Apple is a global company."

    english_embeddings = get_embeddings_for_text(english_text, nlp_en, glove_embeddings)

    print("English Embeddings:")
    for w, embedding in english_embeddings.items():
        print(f"{w}: {embedding[:5]}...")  # Print only the first 5 dimensions

"""
English Embeddings:
Apple: [-0.245    0.50555 -0.11252  0.21967 -0.21182]...
is: [-0.084961   0.502      0.0023823 -0.16755    0.30721  ]...
a: [ 0.043798  0.024779 -0.20937   0.49745   0.36019 ]...
global: [-0.38819  0.45681  0.41941  0.30742  0.58854]...
company: [-0.010464  0.39163  -0.33662  -0.84683   0.15433 ]...
.: [ 0.012001  0.20751  -0.12578  -0.59325   0.12525 ]...

"""
