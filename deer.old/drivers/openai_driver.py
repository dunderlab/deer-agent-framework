import os
from typing import Optional

from .base_driver import OpenAIStandardDriver


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
            "Content-Type": "application/json"
        }

    def __repr__(self) -> str:
        return "OpenAI"
