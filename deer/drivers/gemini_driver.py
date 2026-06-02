import json
import os
from typing import TypeVar, Type, Optional

from pydantic import BaseModel

from .base_driver import LLMDriver, logger

T = TypeVar("T", bound=BaseModel)


class GeminiDriver(LLMDriver):
    def __init__(self, model_name: str, api_version: str = "v1beta"):
        super().__init__(model_name)
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable is not set.")

        # Setup the definitive REST endpoint for Gemini
        self.url = f"https://generativelanguage.googleapis.com/{api_version}/models/{self.model_name}:generateContent?key={self.api_key}"

    def __repr__(self) -> str:
        return "Gemini"

    def generate_text(self, prompt: str) -> str:
        logger.debug(f"Generating text with model {self.model_name} and prompt: {prompt}")

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseMimeType": "text/plain"}
        }

        try:
            response_json = self._send_post_request(self.url, payload)
            return response_json["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as e:
            logger.error(f"Unexpected response structure from Gemini API: {e}")
            raise RuntimeError("Failed to parse text from Gemini API response.")

    def generate_json(self, prompt: str, response_model: Optional[Type[T]] = None) -> T:
        logger.debug(f"Generating JSON with model {self.model_name} and prompt: {prompt}")

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseMimeType": "application/json"}
        }

        if response_model:
            payload["generationConfig"]["responseSchema"] = response_model.model_json_schema()

        try:
            response_json = self._send_post_request(self.url, payload)
            response_text = response_json["candidates"][0]["content"]["parts"][0]["text"]
            data = json.loads(response_text)
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            logger.error(f"Error parsing JSON response from Gemini: {e}")
            raise RuntimeError(f"Error processing JSON output from Gemini: {e}")

        if response_model:
            data = response_model.model_validate(data)

        return data