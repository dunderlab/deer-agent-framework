from typing import Generator, TypeVar
import os

from pydantic import BaseModel

from deer.models import ChatMessage
from .base import LLMDriver

T = TypeVar("T", bound=BaseModel)


class GeminiDriver(LLMDriver):
    def __init__(self, model_name: str, api_version: str = "v1beta"):
        super().__init__(model_name)
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable is not set.")

        # Setup the definitive REST endpoint for Gemini
        self.api_version = api_version

    @property
    def url(self) -> str:
        return f"https://generativelanguage.googleapis.com/{self.api_version}/models/{self.model_name}:generateContent?key={self.api_key}"

    def __repr__(self) -> str:
        return "Gemini"

    def generate(
        self,
        messages: list[ChatMessage],
        response_model: type[T] | None = None,
    ) -> str | T:
        return ""

    def generate_stream(
        self,
        messages: list[ChatMessage],
    ) -> Generator[str, None, None]:
        pass
