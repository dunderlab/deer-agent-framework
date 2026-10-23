import os
from typing import Generator, TypeVar, Callable
import json
import urllib.request

from pydantic import BaseModel

from deer.models import ChatMessage
from .base import LLMDriver, logger

T = TypeVar("T", bound=BaseModel)


class BaseOllama:
    model_name: str
    temperature: float | int
    top_p: float | int
    extract_json: Callable[[str], str]
    _send_post_request: Callable[[dict], str | T]
    _send_streaming_request: Callable[[dict], Generator[bytes, None, None]]

    def generate(
        self,
        messages: list[ChatMessage],
        response_model: type[T] | None = None,
    ) -> str | T:
        """
        Generates a response from Ollama.
        If response_model is provided, it forces the model to follow the schema.
        """
        logger.debug("Generating response with Ollama model %s", self.model_name)

        # Base payload for /api/chat
        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": False,  # Must be False for deterministic programmatic access
            "options": {
                "temperature": self.temperature,
                "top_p": self.top_p,
            },
        }

        # FORCE SCHEMA: In Ollama, the 'format' field can take a JSON Schema directly
        if response_model:
            # Generate the JSON Schema from the Pydantic model
            payload["format"] = response_model.model_json_schema()

        try:
            # Ollama doesn't require special headers for local use, but we use the base helper
            response_json = self._send_post_request(payload)

            # Ollama /api/chat response structure: {"message": {"role": "assistant", "content": "..."}}
            content = response_json["message"]["content"]

            if response_model:
                # Strict validation: Convert the JSON string to a Pydantic object
                # return response_model.model_validate_json(content)
                clean_json_str = self.extract_json(content)
                return response_model.model_validate_json(clean_json_str)

            return content

        except (KeyError, RuntimeError) as e:
            logger.error("Ollama structured output failed: %s", e)
            raise RuntimeError(
                f"Ollama failed to follow the deterministic contract: {e}"
            ) from e

    def generate_stream(
        self,
        messages: list[ChatMessage],
    ) -> Generator[str, None, None]:
        """
        Implementation of streaming for Ollama.
        Yields tokens as they arrive from the API.
        """
        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": True,
            "options": {"temperature": self.temperature, "top_p": self.top_p},
        }

        try:
            # Use the new streaming helper from the base class
            for line in self._send_streaming_request(payload):
                if not line:
                    continue

                # Parse each JSON chunk from Ollama
                chunk = json.loads(line.decode("utf-8"))

                # Ollama structure: {"message": {"role": "assistant", "content": "..."}}
                if "message" in chunk and "content" in chunk["message"]:
                    yield chunk["message"]["content"]

        except Exception as e:
            logger.error("Ollama streaming failed: %s", e)
            yield f"\n[ERROR]: Stream interrupted: {e}"


class OllamaLocalDriver(BaseOllama, LLMDriver):
    def __init__(
        self,
        model_name: str,
        host: str = "http://localhost:11434",
        temperature: float = 0.0,
        top_p: float = 1.0,
    ):
        super().__init__(model_name, temperature, top_p)
        self.base_url = host.rstrip("/")

    @property
    def url(self) -> str:
        return f"{self.base_url}/api/chat"

    def __repr__(self) -> str:
        return f"Ollama [Local] | {self.model_name}"

    def unload_model(self):
        payload = {"model": self.model_name, "keep_alive": 0}
        data = json.dumps(payload).encode("utf-8")

        req = urllib.request.Request(
            self.url, data=data, headers=self.headers, method="POST"
        )

        try:
            # Execute the HTTP request
            with urllib.request.urlopen(req) as response:
                response_body = response.read().decode("utf-8")
                logger.info("Model unloaded successfully from memory.")
                print(response_body)
        except Exception as e:
            logger.warning(f"Failed to communicate with Ollama: {e}")


class OllamaKeyDriver(BaseOllama, LLMDriver):
    def __init__(
        self,
        model_name: str,
        temperature: float = 0.0,
        top_p: float = 1.0,
    ):
        self.api_key = os.getenv("OLLAMA_API_KEY")
        if not self.api_key:
            raise ValueError("OLLAMA_API_KEY environment variable is not set.")

        super().__init__(model_name.rstrip("-cloud"), temperature, top_p)

    @property
    def url(self) -> str:
        return "https://api.ollama.com/api/chat"

    @property
    def headers(self) -> dict:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "User-Agent": "curl/8.4.0",
        }

    def __repr__(self) -> str:
        return f"Ollama [Key] | {self.model_name}"
