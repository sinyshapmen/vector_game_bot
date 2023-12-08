import numpy as np
from openai import OpenAI
from openai import BadRequestError, RateLimitError
import torchtext
import nltk
from nltk.stem import WordNetLemmatizer


class OpenaiClient:
    def __init__(self, api_key):
        nltk.download("wordnet")
        self.__lemmatizer = WordNetLemmatizer()
        self.__api_key = api_key
        self.__client = OpenAI(api_key=self.__api_key)
        self.__glove = torchtext.vocab.GloVe(
            name="42B", dim=300  # trained on Wikipedia 2014 corpus of 42 billion words
        )

    def generate_image(
        self, prompt, model="dall-e-3", size="1024x1024", quality="standard", n=1
    ) -> str:
        try:
            response = self.__client.images.generate(
                model=model,
                prompt=prompt,
                size=size,
                quality=quality,
                n=n,
            )
        except BadRequestError as e:
            return [400, e.code]
        except RateLimitError as e:
            return [429, e.code]
        except Exception as e:
            return [500, e]
        else:
            return [200, response.data[0].url]

    def get_embedding(self, word: str):
        word = self.__lemmatizer.lemmatize(word.replace("\n", " "))
        return self.__glove[word]

    def activation(self, x: float, b: float = 0.4, n: float = 8.0) -> float:
        return 1 / (1 + np.exp(-n * (x - b)))

    def cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        similarity = np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
        similarity = self.activation(similarity) / self.activation(1)
        return 0.99 if similarity > 0.99 else similarity

    @staticmethod
    def exist(x):
        return x.any()
