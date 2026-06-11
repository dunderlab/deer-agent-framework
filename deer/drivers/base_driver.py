from typing import Protocol, Type, TypeVar
import re
import json
import urllib.request
import urllib.error
from typing import TypeVar, Type, Optional, Any
import logging

from pydantic import BaseModel

# T represents any class inheriting from BaseModel
T = TypeVar("T", bound=BaseModel)
logger = logging.getLogger("DEER-LLM")


class LLMDriver(Protocol):
    """Contract for drivers supporting Architectural Brilliance."""

    temperature_json = 0.0
    top_p = 1.0

    def __init__(self, model_name: str):
        self.model_name = model_name

    def _send_post_request(
        self, url: str, payload: dict, headers: Optional[dict] = None
    ) -> dict:
        """Centralized helper to handle HTTP POST requests for all drivers."""
        if headers is None:
            headers = {"Content-Type": "application/json"}
        else:
            headers.setdefault("Content-Type", "application/json")

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers)

        try:
            with urllib.request.urlopen(req) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8")
            logger.error(f"HTTP Error {e.code}: {error_body}")
            raise RuntimeError(f"API request failed with status {e.code}: {error_body}")
        except urllib.error.URLError as e:
            logger.error(f"URL Error: {e.reason}")
            raise RuntimeError(f"Failed to reach server: {e.reason}")

    def generate_text(self, prompt: str) -> str:
        raise NotImplementedError("Subclasses must implement generate_text")

    def generate_json(self, prompt: str, response_model: Optional[Type[T]] = None) -> T:
        raise NotImplementedError("Subclasses must implement generate_json")

    def extract_json(self, text: str) -> dict:
        text = text.strip()
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"^json\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            raise RuntimeError(
                f"Failed to parse JSON from response: {e}, response: {text}"
            )


class OpenAIStandardDriver(LLMDriver):
    """Base driver for OpenAI-compatible APIs."""

    def __init__(self, model_name: str):
        super().__init__(model_name)
        # Use defaults from LLMDriver protocol if not set
        self.temperature_json = getattr(self, "temperature_json", 0.0)
        self.top_p = getattr(self, "top_p", 1.0)

    @property
    def url(self) -> str:
        raise NotImplementedError("Subclasses must implement url property")

    @property
    def headers(self) -> dict:
        raise NotImplementedError("Subclasses must implement headers property")

    def generate_text(self, prompt: str) -> str:
        logger.debug(
            f"Generating text with model {self.model_name} and prompt: {prompt}"
        )

        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
        }

        try:
            response_json = self._send_post_request(
                self.url, payload, headers=self.headers
            )
            return response_json["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as e:
            logger.error(f"Unexpected response structure from API: {e}")
            raise RuntimeError(f"Failed to parse text from API response: {e}")

    def generate_json(self, prompt: str, response_model: Optional[Type[T]] = None) -> T:
        logger.debug(
            f"Generating JSON with model {self.model_name} and prompt: {prompt}"
        )

        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"},
            "temperature": self.temperature_json,
            "top_p": self.top_p,
        }

        try:
            response_json = self._send_post_request(
                self.url, payload, headers=self.headers
            )
            response_text = response_json["choices"][0]["message"]["content"]
            data = json.loads(response_text)
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            logger.error(f"Error parsing JSON response from API: {e}")
            # Try fallback extraction
            try:
                # We need to reach the response_text if it was already assigned before error
                if "response_text" in locals():
                    data = self.extract_json(response_text)
                else:
                    raise
            except Exception:
                raise RuntimeError(f"Error processing JSON output from API: {e}")

        if response_model:
            data = response_model.model_validate(data)

        return data
