import json
import time
import base64
import requests


class KandinskyClient:
    def __init__(self, url, api_key, secret_key):
        self.api_key = api_key
        self.secret_key = secret_key
        self.URL = url
        self.AUTH_HEADERS = {
            "X-Key": f"Key {api_key}",
            "X-Secret": f"Secret {secret_key}",
        }

    def get_model(self):
        response = requests.get(
            self.URL + "key/api/v1/models", headers=self.AUTH_HEADERS
        )
        data = response.json()
        return data[0]["id"]

    def generate(self, prompt: str, model, images=1, width=1024, height=1024):
        params = {
            "type": "GENERATE",
            "numImages": images,
            "width": width,
            "height": height,
            "generateParams": {"query": f"{prompt}"},
        }

        data = {
            "model_id": (None, model),
            "params": (None, json.dumps(params), "application/json"),
        }
        response = requests.post(
            self.URL + "key/api/v1/text2image/run",
            headers=self.AUTH_HEADERS,
            files=data,
        )
        data = response.json()
        return data["uuid"]

    def check_generation(self, request_id: str, attempts: int = 10, delay: int = 10):
        while attempts > 0:
            response = requests.get(
                self.URL + "key/api/v1/text2image/status/" + request_id,
                headers=self.AUTH_HEADERS,
            )
            data = response.json()
            if data["status"] == "DONE":
                return [data["images"], data["censored"]]

            attempts -= 1
            time.sleep(delay)

    def generate_image(self, prompt: str) -> tuple:
        try:
            model_id = self.get_model()
            uuid = self.generate(prompt, model_id)
            images, censored = self.check_generation(uuid)

            image_data = base64.b64decode(images[0])

            return 400 if censored else 200, image_data
        except Exception as e:
            return 500, e
