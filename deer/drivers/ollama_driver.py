import json
from typing import TypeVar, Type
import logging

from ollama import Client
from pydantic import BaseModel

from .base_driver import LLMDriver

T = TypeVar("T", bound=BaseModel)

logger = logging.getLogger("DEER-LLM")


class OllamaDriver(LLMDriver):
    def __init__(
        self,
        model_name: str,
        host: str = "http://localhost:11434",
    ):
        self.client = Client(host=host)
        self.model_name = model_name

    def generate_text(self, prompt: str) -> str:
        logger.debug(
            f"Generating text with model {self.model_name} and prompt: {prompt}"
        )

        response = self.client.generate(
            model=self.model_name,
            prompt=prompt,
        )

        return response["response"]

    def generate_json(
        self,
        prompt: str,
        response_model: Type[T] = None,
    ) -> T:
        logger.debug(
            f"Generating JSON with model {self.model_name} and prompt: {prompt}"
        )

        response = self.client.generate(
            model=self.model_name,
            prompt=prompt,
            format="json",
            options={
                "temperature": self.temperature_json,
                "top_p": self.top_p,
            },
        )
        response_text = response["response"]
        # response_text = self.escape_logic(response_text)

        try:
            data = json.loads(response_text)
        except json.JSONDecodeError as e:
            data = self.extract_json(response_text)

        if response_model:
            data = response_model.model_validate(data)

        return data
