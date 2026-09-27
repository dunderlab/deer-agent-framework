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
        self.api_version = api_version

    @property
    def url(self) -> str:
        return f"https://generativelanguage.googleapis.com/{self.api_version}/models/{self.model_name}:generateContent?key={self.api_key}"

    def __repr__(self) -> str:
        return "Gemini"
