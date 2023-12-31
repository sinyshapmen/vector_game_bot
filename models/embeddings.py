import numpy as np
import nltk
import torchtext


class Embeddings:
    def __init__(self):
        nltk.download("wordnet")
        self.__glove = torchtext.vocab.GloVe(
            name="6B", dim=50  # trained on Wikipedia 2014 corpus of 6 billion words
        )

    def get_embedding(self, word: str):
        return self.__glove[word]

    def activation(self, x: float, b: float = 0.4, n: float = 8.0) -> float:
        return 1 / (1 + np.exp(-n * (x - b)))

    def cosine_similarity(self, a, b) -> float:
        similarity = np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
        similarity = self.activation(similarity) / self.activation(1)
        return 0.99 if similarity > 0.99 else similarity

    @staticmethod
    def exist(x):
        return x.any()
