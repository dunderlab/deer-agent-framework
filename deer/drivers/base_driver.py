import re
import json
import logging
import urllib.error
import urllib.request
from typing import TypeVar, Type, Optional, Protocol

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
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8")
            logger.error(f"HTTP Error {e.code}: {error_body}")
            raise RuntimeError(f"API request failed with status {e.code}: {error_body}")
        except urllib.error.URLError as e:
            logger.error(f"URL Error: {e.reason}")
            raise RuntimeError(f"Failed to reach server: {e.reason}")

    #
    # def _send_post_request(
    #     self, url: str, payload: dict, headers: Optional[dict] = None
    # ) -> dict:
    #     """
    #     Centralized helper to handle HTTP POST requests for all drivers.
    #     Using httpx for better signal handling and robust timeout management.
    #     """
    #     # If headers are provided, we use them; otherwise, we let httpx handle JSON defaults.
    #     # Note: httpx automatically sets 'Content-Type: application/json' when using the json= parameter.
    #     request_headers = headers if headers is not None else {}
    #
    #     try:
    #         # We use a Client instance for better connection pooling and timeout control
    #         with httpx.Client(timeout=30.0) as client:
    #             # 'json=payload' automatically handles json.dumps and encodes to utf-8
    #             response = client.post(url, json=payload, headers=request_headers)
    #
    #             # This raises an httpx.HTTPStatusError if the response is 4xx or 5xx
    #             response.raise_for_status()
    #
    #             # Return the parsed JSON dictionary
    #             return response.json()
    #
    #     except httpx.TimeoutException:
    #         # Specifically catch timeouts so the user knows the server is slow
    #         logger.error(f"Request to {url} timed out.")
    #         raise RuntimeError("The server took too long to respond (Timeout).")
    #
    #     except httpx.HTTPStatusError as e:
    #         # Handle 4xx and 5xx errors (replaces urllib.error.HTTPError)
    #         error_body = e.response.text
    #         logger.error(f"HTTP Error {e.response.status_code}: {error_body}")
    #         raise RuntimeError(
    #             f"API request failed with status {e.response.status_code}: {error_body}"
    #         )
    #
    #     except httpx.RequestError as e:
    #         # Handle connection errors, DNS issues, etc. (replaces urllib.error.URLError)
    #         logger.error(f"Network request error: {e}")
    #         raise RuntimeError(f"Failed to reach the server: {e}")
    #
    #     except json.JSONDecodeError:
    #         # Handle cases where the server returns 200 OK but the body isn't valid JSON
    #         logger.error("Server returned a successful status but invalid JSON body.")
    #         raise RuntimeError("Server returned an invalid JSON response.")
    #
    #     except Exception as e:
    #         # Crucial: if it's a KeyboardInterrupt, re-raise it immediately so the REPL catches it
    #         if isinstance(e, KeyboardInterrupt):
    #             raise e
    #
    #         logger.error(f"Unexpected error during POST request: {e}")
    #         raise RuntimeError(f"An unexpected network error occurred: {e}")

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
