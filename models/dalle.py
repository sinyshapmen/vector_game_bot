from http import client
from openai import OpenAI
from openai import BadRequestError, RateLimitError
import requests


class OpenaiClient:
    def __init__(self, api_key):
        self.__api_key = api_key
        self.__client = OpenAI(api_key=self.__api_key)

    def generate_image(self, prompt, model="dall-e-3", n=1) -> list:
        try:
            response = self.__client.images.generate(
                model=model,
                prompt=prompt,
                size="1024x1024",
                quality="standard",
                n=n,
            )
            image_url = response.data[0].url
            image = requests.get(str(image_url))
            if image.status_code == 200:
                return 200, image.content
        except BadRequestError as e:
            return 400, e.code
        except RateLimitError as e:
            return 429, e.code
        except Exception as e:
            return 500, e
        else:
            return 200, response.data[0].url
