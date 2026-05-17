import re
import json
from typing import TypeVar, Type

from pydantic import BaseModel
from google import genai

from .base_driver import LLMDriver

T = TypeVar("T", bound=BaseModel)


class GeminiDriver(LLMDriver):
    def __init__(self, model_name="gemini-2.0-flash"):
        self.client = genai.Client()
        self.model_name = model_name

    def generate(self, prompt: str, response_model: Type[T] = None) -> T:

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                # "response_schema": response_model.model_json_schema(),
            },
        )

        response_text = response.text
        response_text = escape_logic(response_text)

        data = json.loads(response_text)

        if response_model is None:
            return data

        return response_model.model_validate(data)


def escape_logic(text: str) -> str:
    text = text.replace('"""', '\\"\\"\\"')
    return text
