import os
from typing import Optional

from .base_driver import OpenAIStandardDriver


class AzureOpenAIDriver(OpenAIStandardDriver):
    def __init__(
        self,
        model_name: str,
        api_version: str = "2024-02-15-preview"
    ):
        super().__init__(model_name)
        self.api_key = os.getenv("AZURE_OPENAI_API_KEY")
        self.endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.api_version = api_version

        if not self.api_key:
            raise ValueError("AZURE_OPENAI_API_KEY environment variable is not set.")
        if not self.endpoint:
            raise ValueError("AZURE_OPENAI_ENDPOINT environment variable is not set.")

        # In Azure, the "model" in the payload is often ignored in favor of the deployment in the URL,
        # but we keep it for compatibility with the base class logic.
        self.base_url = self.endpoint.rstrip("/")

    @property
    def url(self) -> str:
        # Azure URL format: {endpoint}/openai/deployments/{deployment_id}/chat/completions?api-version={api_version}
        # We assume model_name is the deployment name.
        return f"{self.base_url}/openai/deployments/{self.model_name}/chat/completions?api-version={self.api_version}"

    @property
    def headers(self) -> dict:
        return {
            "api-key": self.api_key,
            "Content-Type": "application/json"
        }

    def __repr__(self) -> str:
        return "AzureOpenAI"
