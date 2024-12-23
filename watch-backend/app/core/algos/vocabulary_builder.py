import logging
import re
from dataclasses import dataclass
from itertools import chain
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import spacy
from PyDictionary import PyDictionary
from spacy.tokens import Span, Token
from word_forms.word_forms import get_word_forms

from app.core.utils.pos_align import align_pos

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_freq_lookup() -> Dict[str, float]:
    freq = pd.read_csv('../../resources/subtlexus.csv')
    return {w: f for w, f in freq[['Word', 'Lg10WF']].to_numpy()}

def dictionary_lookup(word: str) -> List[Tuple[str, str]]:
    dictionary = PyDictionary()
    lookup = dictionary.meaning(word)
    return list(lookup.items())

class Word:
    def __init__(self, word: Token, cefr_file_path: str):
        self.text: str = word.text
        self.pos: str = word.tag_
        self.lemma: str = self._get_lemma(word)
        self.embeddings: Floats1d = word.vector
        self._sentences: List[Sentence] = []
        self.cefr: Optional[str] = self._fetch_cefr_from_dataset(cefr_file_path)

    @staticmethod
    def _get_lemma(word: Token) -> str:
        """Get canonical lemma form using word_forms"""
        word_forms = get_word_forms(word.text).values()
        flat_list_of_forms = list(set(chain.from_iterable(word_forms)))
        if len(flat_list_of_forms) > 3:
            return sorted(flat_list_of_forms, key=len)[0]
        return word.lemma_

    @property
    def complexity(self) -> float:
        """Get the complexity of the word."""
        freq_subtlexus = load_freq_lookup()
        if self.text in freq_subtlexus:
            return 5 - freq_subtlexus[self.text]

        # Calculate the mean of the distribution of freq_subtlexus values
        if freq_subtlexus:  # Ensure freq_subtlexus is not empty
            mean_freq_subtlexus = sum(freq_subtlexus.values()) / len(freq_subtlexus)
            return 5 - mean_freq_subtlexus  # Complexity as 5 minus the mean frequency

        # Fallback if freq_subtlexus is unexpectedly empty
        return 2.5

    def _fetch_cefr_from_dataset(self, path: str) -> Optional[str]:
        """
        Looks up the CEFR level for the word in the resources based on its text and POS.

        Args:
            path (str): Path to the CEFR resources CSV file.

        Returns:
            Optional[str]: The CEFR level (e.g., A1, B1, C2) if found, otherwise None.
        """
        try:
            # Check for the required columns
            if 'headword' not in cefr_data.columns or 'pos' not in cefr_data.columns or 'CEFR' not in cefr_data.columns:
                raise ValueError("The CEFR resources must contain 'headword', 'pos', and 'CEFR' columns.")

            # Filter resources for matching headword and POS
            record = cefr_data[(cefr_data['headword'].str.lower() == self.lemma.lower())]
            # Get the mapping between pos tags of CEFR-J dataset and Spacy.
            mapping = align_pos()

            # Further filter records where self.pos.lower() exists in the corresponding POS mapping
            record = record[record['pos'].apply(lambda pos: self.pos in mapping.get(pos, []))]

            # Return the CEFR level if a match is found
            if not record.empty:
                return record.iloc[0]['CEFR']  # Return the first match's CEFR level
            else:
                return None
        except FileNotFoundError:
            raise FileNotFoundError(f"The file at path '{path}' was not found.")
        except Exception as e:
            raise RuntimeError(f"An error occurred while processing the CEFR resources: {e}")

    @property
    def frequency(self) -> int:
        """Get document frequency"""
        return len(self._sentences)

    def get_sentences(self, network=None):
        """Return a ranked sentence"""
        if network:
            for idx, sent in enumerate(self._sentences):
                mean_mastery = np.mean([network.node[lemma]["mastery"] for lemma in sent.lemmas if lemma in network])
                self._sent_errs[idx].update({"known": 1 - mean_mastery})

        # Rank
        ranked_sentences = sorted(
            set((Word.sent_err(y), str(y), x.text) for x, y in zip(self._sentences, self._sent_errs)))
        # ranked_sentences = [x for x,_ in sorted(zip(self._sentences, self._sent_errs), key=lambda pair: Word.sent_err(pair[1]))]

        print("Sentences selected for %s: " % (self.text))
        for score, attrb, sent in ranked_sentences[::-1]:
            print("%s\n%s\t%s\n\n" % (str(attrb), score, sent))

        return [x for _, _, x in ranked_sentences]

    def include_sentence(self, sentence):
        """Include the sentence to the list of evidences for the word."""

        # Calculate sentence selection metrics
        has_PRON = 1 if 'PRON' in sentence.pos_tags else 0
        is_regular = 0 if ((sentence.tokens[0].isalpha() or sentence.tokens[0] in ['"', '“']) and sentence.pos_tags[
            -1] == 'PUNCT') else 1

        # Length penalty
        length = sum(1 for pos in sentence.pos_tags if pos not in ['PART', 'PUNCT', 'SPACE', 'NUM', 'SYM'])
        a, b, c = 10, 15, 10.0
        length_err = min(max(a - length, 0, length - b) / c, 1)

        # Distance to end
        target_pos = float(sentence.tokens.index(self.text) + 1)
        # position_err = 1 - (target_pos/len(sentence.tokens))
        position_err = (target_pos / len(sentence.tokens))

        self._sent_errs.append({"length": length_err,
                                "known": 0,
                                "position": position_err,
                                "punctuation": is_regular,
                                "anaphora": has_PRON})
        self._sentences.append(sentence)


@dataclass
class Sentence:
    """ Maintains the attributes of a sentence and also points to the adjacent
    sentences in the subtitle."""
    def __init__(self):
        self.text: str = Sentence.clean(sentence_obj.text)
        self.word_count = len(sentence_obj)
        slef.next_sent = None
        self.pos_tags = [tok.pos_ for tok in sentence_obj if not tok.pos_ in ["SPACE"]]
        self.tokens = [tok.text for tok in sentence_obj]
        self.lemmas = [Word.get_lemma(tok) for tok in sentence_obj
                       if tok.text not in STOP_WORDS and tok.pos_ not in ['PART', 'PUNCT', 'SPACE', 'NUM', 'SYM']]

        if previous_sentence:
            self.prev_sent: Optional['Sentence'] = previous_sentence
            self.prev_sent.next_sent = self

    @staticmethod
    def clean(text):
        clean = text.strip().lower() # capitalize()?


        pattern = re.compile(r'[\r\n]')
        clean = pattern.sub(' ', clean)
        return clean

    @staticmethod
    def from_spacy(sent: Span, previous_sentence: Optional['Sentence'] = None) -> 'Sentence':
        """Create Sentence from spaCy span"""
        sentence = Sentence(
            text=sent.text.strip().capitalize(),
            tokens=[token.text for token in sent],
            pos_tags=[token.pos_ for token in sent if token.pos_ != "SPACE"],
            lemmas=[Word._get_lemma(token) for token in sent
                    if not token.is_stop and token.pos_ not in ['PART', 'PUNCT', 'SPACE', 'NUM', 'SYM']],
            word_count=len(sent),
            prev_sent=previous_sentence
        )
        if previous_sentence:
            previous_sentence.next_sent = sentence
        return sentence


# class WordFamily:
#     """Enhanced Family class with typing"""
#
#     def __init__(self, root: str, cefr_level: Optional[str] = None):
#         self.root: str = root
#         self.members: List[Word] = []
#         self.cefr_level: Optional[str] = cefr_level
#
#     def add_member(self, word: Word) -> None:
#         """Add a word to the family"""
#         self.members.append(word)
#
#     @property
#     def vector(self) -> np.ndarray:
#         """Get family vector representation"""
#         return np.mean([member.vector for member in self.members], axis=0)
#
#     @property
#     def complexity(self) -> float:
#         """Get family complexity"""
#         return np.mean([member.complexity for member in self.members])


# class CEFRVocabBuilder:
#     """Main class for building CEFR-aware vocabulary networks"""
#
#     def __init__(self, nlp: spacy.Language):
#         self.nlp: spacy.Language = nlp
#         self.word_info: Dict[str, WordInfo] = {}
#         self.words: Dict[str, Word] = {}
#         self.families: Dict[str, WordFamily] = {}
#         self.network: Optional[nx.Graph] = None
#
#     def load_cefr_data(self, csv_path: Union[str, Path]) -> None:
#         """Load CEFR data from CSV"""
#         df = pd.read_csv(csv_path)
#         for _, row in df.iterrows():
#             key = f"{row['headword'].lower()} ; {row['pos']}"
#             self.word_info[key] = WordInfo(
#                 headword=row['headword'].lower(),
#                 pos=row['pos'],
#                 cefr=row['CEFR']
#             )
#
#     def process_text(self, text: str) -> None:
#         """Process text and build vocabulary network"""
#         logger.info("Processing text...")
#         doc = self.nlp(text.lower())
#
#         prev_sent: Optional[Sentence] = None
#         for sent in doc.sents:
#             curr_sent = Sentence.from_spacy(sent, prev_sent)
#
#             for token in sent:
#                 if token.is_stop or token.pos_ in ['PART', 'PUNCT', 'SPACE', 'NUM', 'SYM']:
#                     continue
#
#                 key = f"{token.text.strip()} ; {token.tag_}"
#                 if key not in self.words:
#                     word_info = self.word_info.get(key)
#                     self.words[key] = Word(token, word_info)
#                 self.words[key].add_sentence(curr_sent)
#
#             prev_sent = curr_sent
#
#         self._build_families()
#         self._build_network()
#
#     def _build_families(self) -> None:
#         """Build word families"""
#         logger.info("Building word families...")
#         for word in self.words.values():
#             if word.frequency < 5:  # Minimum frequency threshold
#                 continue
#
#             key = word.lemma
#             if key not in self.families:
#                 self.families[key] = WordFamily(key)
#             self.families[key].add_member(word)
#
#     def _build_network(self, min_similarity: float = 0.3, max_connections: int = 5) -> None:
#         """Build word family network with similarity edges"""
#         logger.info("Building network...")
#
#         vectors = np.array([family.vector for family in self.families.values()])
#         norms = np.linalg.norm(vectors, axis=1)
#         normalized_vectors = vectors / norms[:, np.newaxis]
#         similarity_matrix = np.dot(normalized_vectors, normalized_vectors.T)
#
#         # Create network
#         self.network = nx.Graph()
#         self.network.add_nodes_from(self.families.keys())
#
#         # Add edges based on similarity
#         family_names = list(self.families.keys())
#         for i, f1 in enumerate(family_names):
#             edges = []
#             for j, f2 in enumerate(family_names[i + 1:], i + 1):
#                 sim_score = similarity_matrix[i][j]
#                 if sim_score > min_similarity:
#                     edges.append((f2, sim_score))
#
#             # Add top K most similar connections
#             for f2, score in sorted(edges, key=lambda x: -x[1])[:max_connections]:
#                 self.network.add_edge(f1, f2, weight=score)
#
#     def save_network(self, path: Union[str, Path]) -> None:
#         """Save network to GEXF format"""
#         if self.network:
#             nx.write_gexf(self.network, path)
#
#     def get_stats(self) -> Dict[str, Union[int, List[Tuple[int, str, str]]]]:
#         """Get vocabulary statistics"""
#         freq_list = sorted([(w.frequency, w.text, w.pos) for w in self.words.values()], reverse=True)
#
#         return {
#             'total_words': len(self.words),
#             'total_families': len(self.families),
#             'words_above_freq5': sum(1 for w in self.words.values() if w.frequency > 5),
#             'words_above_freq10': sum(1 for w in self.words.values() if w.frequency > 10),
#             'most_frequent': freq_list[:15],
#             'least_frequent': freq_list[-15:]
#         }


if __name__ == "__main__":
    path = Path(__file__).resolve().parent.parent.parent.joinpath("resources/CEFR_combined_data.csv")
    cefr_data = pd.read_csv(path)
    # Create a Word instance
    nlp = spacy.load("en_core_web_lg")
    doc = nlp("Calculating the CEFR level of a word is easy.")
    token = doc[0]
    w = Word(
        token,
        cefr_file_path=path
    )

    # Print the word and its attributes
    print("Word:", w.text)
    print("POS:", w.pos)
    print("Lemma:", w.lemma)

    # print("Embeddings:", w.embeddings)
    print("CEFR:", w.cefr)

    # print("Occurrences:", w.occurrences)
    print("Frequency:", w.frequency)  # Derived attribute
    print("Complexity (default):", w.complexity)
    # print("Mastery (default):", w.mastery)