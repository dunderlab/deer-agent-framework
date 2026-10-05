from typing import TypeVar
import os

from pydantic import BaseModel

from deer.models import ChatMessage
from .base import OpenAIStandardDriver

T = TypeVar("T", bound=BaseModel)


class OpenAIDriver(OpenAIStandardDriver):
    def __init__(self, model_name: str):
        super().__init__(model_name)
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set.")

    @property
    def url(self) -> str:
        return "https://api.openai.com/v1/chat/completions"

    @property
    def headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def __repr__(self) -> str:
        return "OpenAI"

    def generate(
        self,
        messages: list[ChatMessage],
        response_model: type[T] | None = None,
    ) -> str | T:
        return ""
