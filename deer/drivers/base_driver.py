import json
import logging
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from typing import TypeVar, Type, Optional, Union, Generator

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)
logger = logging.getLogger("DEER-LLM")

Message = dict[str, str]


class LLMDriver(ABC):
    def __init__(
        self, model_name: str, temperature: float = 0.0, top_p: float = 1.0
    ) -> None:
        self.model_name = model_name
        self.temperature = temperature
        self.top_p = top_p

    @property
    def url(self) -> str:
        raise NotImplementedError()

    @property
    def headers(self) -> dict:
        return {
            "Content-Type": "application/json"
        }

    def _send_post_request( self, payload: dict) -> dict:

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(self.url, data=data, headers=self.headers)

        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as e:
            logger.error(f"Request error: {e}")
            raise RuntimeError(f"API request failed: {e}")

    def _send_streaming_request(
        self, payload: dict
    ) -> Generator[bytes, None, None]:
        """
        Low-level helper to handle streaming HTTP requests.
        Yields raw bytes line by line from the server.
        """
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(self.url, data=data, headers=self.headers)

        try:
            # We do NOT use 'with' here in the same way because we want to yield from the response
            response = urllib.request.urlopen(req, timeout=30)
            for line in response:
                yield line
            response.close()
        except Exception as e:
            logger.error(f"Streaming request error: {e}")
            raise RuntimeError(f"Streaming connection failed: {e}")

    @abstractmethod
    def generate(
        self, messages: list[Message], response_model: Optional[Type[T]] = None
    ) -> Union[str, T]:
        pass

    @abstractmethod
    def generate_stream(self, messages: list[Message]) -> Generator[str, None, None]:
        """
        Streaming generation.
        Yields tokens as they are received from the API.
        """
        pass


class OpenAIStandardDriver(LLMDriver):

    def generate(
        self, messages: list[Message], response_model: Optional[Type[T]] = None
    ) -> Union[str, T]:
        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": self.temperature,
            "top_p": self.top_p,
        }

        if response_model:
            # TRUE FORCE: Instead of just 'json_object', we send the actual JSON Schema.
            # model_json_schema() generates the standard JSON Schema from the Pydantic model.
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": response_model.__name__,
                    "strict": True,  # Forces the model to follow the schema 100%
                    "schema": response_model.model_json_schema(),
                },
            }

        try:
            response_json = self._send_post_request(
                self.url, payload, headers=self.headers
            )
            content = response_json["choices"][0]["message"]["content"]

            if response_model:
                # Now we are 99.9% sure the JSON is correct, but we still validate it.
                return response_model.model_validate_json(content)

            return content
        except Exception as e:
            logger.error(f"Structured output failed: {e}")
            raise RuntimeError(f"Model failed the strict contract: {e}")
