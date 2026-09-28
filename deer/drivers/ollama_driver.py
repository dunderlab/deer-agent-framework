import json
from typing import TypeVar, Type, Optional, Union, Generator
from pydantic import BaseModel
from .base_driver import LLMDriver, logger, ChatMessage

T = TypeVar("T", bound=BaseModel)


class OllamaDriver(LLMDriver):
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
        return "Ollama"

    def generate(
        self, messages: list[ChatMessage], response_model: Optional[Type[T]] = None
    ) -> Union[str, T]:
        """
        Generates a response from Ollama.
        If response_model is provided, it forces the model to follow the schema.
        """
        logger.debug(f"Generating response with Ollama model {self.model_name}")

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
            logger.error(f"Ollama structured output failed: {e}")
            raise RuntimeError(
                f"Ollama failed to follow the deterministic contract: {e}"
            )

    def generate_stream(
        self, messages: list[dict[str, str]]
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
            logger.error(f"Ollama streaming failed: {e}")
            yield f"\n[ERROR]: Stream interrupted: {e}"
