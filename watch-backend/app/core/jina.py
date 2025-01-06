# Load model directly
from typing import Dict

import numpy as np
from transformers import AutoModel


def retrieve_embeddings_from_jina(tokens: list) -> Dict[str, np.ndarray]:
    model = AutoModel.from_pretrained("jinaai/jina-embeddings-v3",
                                      trust_remote_code=True)

    embeddings = model.encode(tokens)  # task="text-matching"
    # Map words to their corresponding embeddings
    w_to_e = {word: embedding for word, embedding in zip(tokens, embeddings)}

    return w_to_e


# def retrieve_embeddings_from_mbert(tokens: list) -> Dict[str, np.ndarray]:
#     model = AutoModel.from_pretrained("bert-base-multilingual-cased")
#     tokenizer = AutoTokenizer.from_pretrained("bert-base-multilingual-cased")
#
#     # Tokenize the words (required for input to BERT)
#     encoded_inputs = tokenizer(tokens, is_split_into_words=True, return_tensors="pt")
#
#     # Get the model output (embeddings)
#     with torch.no_grad():  # Disable gradients for inference
#         outputs = model(**encoded_inputs)
#
#     # Extract the embeddings (last hidden state)
#     embeddings = outputs.last_hidden_state  # Shape: [batch_size, sequence_length, hidden_size]
#
#     # Map words to their embeddings
#     w_t_e = {word: embedding for word, embedding in zip(english_tokens + chinese_tokens, embeddings[0])}
#     return w_t_e


if __name__ == "__main__":
    # Example list of tokenized words (replace with your actual tokenized words from SpaCy)
    tokens = ["The", "quick", "brown", "fox", "jumps", "over", "the", "lazy", "dog"]
    word_to_embedding = retrieve_embeddings_from_jina(tokens)
    # Print word embeddings
    for word, embedding in word_to_embedding.items():
        print(
            f"Word: {word} => Embedding: {embedding[:5]}...")  # Print first 5 dimensions of each embedding for brevity

    """
    Word: The => Embedding: [ 0.11127143 -0.13837917  0.02580617  0.08644402  0.02549872]...
    Word: quick => Embedding: [ 0.0706908  -0.09369469  0.0506058   0.03753012  0.09109502]...
    Word: brown => Embedding: [ 0.04301903 -0.10715846 -0.06179521  0.01956394  0.03311772]...
    Word: fox => Embedding: [ 0.09987237 -0.12784299  0.02062598  0.11478288  0.08312666]...
    Word: jumps => Embedding: [ 0.03015892 -0.13739403 -0.0030744   0.14555597  0.1074874 ]...
    Word: over => Embedding: [ 0.0703671  -0.12297609  0.00743065  0.09117738  0.04602962]...
    Word: the => Embedding: [ 0.09930057 -0.13259333  0.01411092  0.10255634  0.0334743 ]...
    Word: lazy => Embedding: [ 0.00555504 -0.07817211  0.05219676 -0.00926692  0.03977306]...
    Word: dog => Embedding: [-0.04046784 -0.13470514  0.08716112  0.04231856  0.06426101]...

    """
