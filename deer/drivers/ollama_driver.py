import json
from typing import TypeVar, Type, Optional

from pydantic import BaseModel

from .base_driver import LLMDriver, logger

T = TypeVar("T", bound=BaseModel)


class OllamaDriver(LLMDriver):
    def __init__(self, model_name: str, host: str = "http://localhost:11434"):
        super().__init__(model_name)
        self.base_url = host.rstrip("/")
        self.url = f"{self.base_url}/api/generate"

        # Default fallback values for generation options if not defined externally
        self.temperature_json = getattr(self, "temperature_json", 0.2)
        self.top_p = getattr(self, "top_p", 0.9)

    def __repr__(self) -> str:
        return "Ollama"

    def generate_text(self, prompt: str) -> str:
        logger.debug(f"Generating text with model {self.model_name} and prompt: {prompt}")

        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False
        }

        response_json = self._send_post_request(self.url, payload)
        return response_json.get("response", "")

    def generate_json(self, prompt: str, response_model: Optional[Type[T]] = None) -> T:
        logger.debug(f"Generating JSON with model {self.model_name} and prompt: {prompt}")

        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self.temperature_json,
                "top_p": self.top_p,
            }
        }

        if response_model:
            payload["format"] = response_model.model_json_schema()
        else:
            payload["format"] = "json"

        response_json = self._send_post_request(self.url, payload)
        response_text = response_json.get("response", "")

        try:
            data = json.loads(response_text)
        except json.JSONDecodeError as e:
            if hasattr(self, "extract_json"):
                data = self.extract_json(response_text)
            else:
                logger.error(f"Failed to decode JSON from response: {e}")
                raise

        if response_model:
            data = response_model.model_validate(data)

        return data