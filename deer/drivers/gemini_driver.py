import json
from typing import TypeVar, Type, reveal_type

from pydantic import BaseModel
from google import genai

from .base_driver import LLMDriver
from .ollama_driver import logger

T = TypeVar("T", bound=BaseModel)


class GeminiDriver(LLMDriver):
    def __init__(self, model_name: str):
        self.client = genai.Client()
        self.model_name = model_name

    def generate_text(self, prompt: str) -> str:
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config={
                    "response_mime_type": "text/plain",
                },
            )
            return response.text
        except genai.errors.ServerError as e:
            logger.error(f"Error generating text with Gemini: {e}")
            return e

    def generate_json(self, prompt: str, response_model: Type[T] = None) -> T:

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                },
            )
        except genai.errors.ServerError as e:
            logger.error(f"Error generating text with Gemini: {e}")
            return {"error": str(e)}

        response_text = response.text
        response_text = self.escape_logic(response_text)
        data = json.loads(response_text)

        if response_model:
            data = response_model.model_validate(data)

        return data
