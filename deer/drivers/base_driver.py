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

    def _send_post_request(self, url: str, payload: dict, headers: Optional[dict] = None) -> dict:
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
        return json.loads(text)
