from typing import Generator, TypeVar
import os

from pydantic import BaseModel

from deer.models import ChatMessage
from .base import LLMDriver, logger

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
        return f"https://generativelanguage.googleapis.com/{self.api_version}/models/{self.model_name}:generateContent"

    @property
    def headers(self) -> dict:
        return {
            "Content-Type": "application/json",
            "x-goog-api-key": self.api_key,
        }

    def __repr__(self) -> str:
        return f"Gemini | {self.model_name}"

    def get_gemini_compatible_schema(self, model: type[BaseModel]) -> dict:
        """
        Flattens a Pydantic model JSON schema and adapts it for the Gemini REST API by:
        1. Inlining $ref pointers and removing $defs.
        2. Converting anyOf with null types into OpenAPI 3.0 compatible 'nullable: true'.
        3. Stripping illegal keywords rejected by Gemini's schema compiler ('title', 'default', 'additionalProperties', etc.).
        """
        schema = model.model_json_schema()
        defs = schema.pop("$defs", {})

        # Keywords strictly forbidden by Gemini's schema validator
        FORBIDDEN_KEYS = {"title", "default", "additionalProperties", "$schema", "$id"}

        def resolve_and_clean(node):
            if isinstance(node, dict):
                # Remove forbidden keys
                for key in FORBIDDEN_KEYS:
                    node.pop(key, None)

                # Handle $ref inlining
                if "$ref" in node:
                    ref_path = node["$ref"]
                    def_name = ref_path.split("/")[-1]
                    if def_name in defs:
                        resolved = defs[def_name].copy()
                        node.clear()
                        node.update(resolve_and_clean(resolved))

                # Handle anyOf with null (convert to nullable: true)
                elif "anyOf" in node:
                    any_of_items = node.pop("anyOf")
                    non_null_items = [
                        item for item in any_of_items if item.get("type") != "null"
                    ]
                    has_null = len(non_null_items) < len(any_of_items)

                    if len(non_null_items) == 1:
                        node.update(resolve_and_clean(non_null_items[0]))
                        if has_null:
                            node["nullable"] = True
                    else:
                        node["anyOf"] = [
                            resolve_and_clean(item) for item in any_of_items
                        ]

                    if has_null and "nullable" not in node:
                        node["nullable"] = True
                else:
                    for k, v in list(node.items()):
                        node[k] = resolve_and_clean(v)

            elif isinstance(node, list):
                for i, item in enumerate(node):
                    node[i] = resolve_and_clean(item)

            return node

        return resolve_and_clean(schema)

    def generate(
        self,
        messages: list[ChatMessage],
        response_model: type[T] | None = None,
    ) -> str | T:
        """
        Generates a response from Gemini via HTTP API.
        Assumes the first message is always 'system' and the rest are 'user' or 'assistant'.
        If response_model is provided, it forces the model to follow the schema.
        """
        logger.debug(
            "Generating response with Gemini model %s via HTTP", self.model_name
        )

        system_instruction = None
        formatted_contents = []

        # 1. Extraer el system instruction (primer mensaje)
        # Acceso mediante atributos de Pydantic (.role.value y .content)
        if messages and messages[0].role.value == "system":
            system_instruction = {"parts": [{"text": messages[0].content}]}
            chat_messages = messages[1:]
        else:
            chat_messages = messages

        # 2. Mapear el resto de mensajes al formato de Gemini ('user' y 'model')
        for msg in chat_messages:
            role_str = msg.role.value if hasattr(msg.role, "value") else str(msg.role)
            role = "model" if role_str == "assistant" else "user"

            formatted_contents.append({"role": role, "parts": [{"text": msg.content}]})

        # 3. Construir el payload base
        payload = {"contents": formatted_contents}

        if system_instruction:
            payload["systemInstruction"] = system_instruction

        # 4. Configuración de generación (temperatura, top_p y esquema estructurado)
        generation_config = {
            "temperature": self.temperature,
            "topP": self.top_p,
        }

        if response_model:
            generation_config["responseMimeType"] = "application/json"
            generation_config["responseSchema"] = self.get_gemini_compatible_schema(
                response_model
            )
            # generation_config["responseSchema"] = response_model.model_json_schema()

        payload["generationConfig"] = generation_config

        try:
            # Envío de la petición POST mediante tu helper interno
            response_json = self._send_post_request(payload)

            # Extracción de la respuesta en la estructura nativa de Gemini REST
            content = response_json["candidates"][0]["content"]["parts"][0]["text"]

            if response_model:
                clean_json_str = self.extract_json(content)
                return response_model.model_validate_json(clean_json_str)

            return content

        except (KeyError, RuntimeError, IndexError) as e:
            # logger.error("Gemini HTTP structured output failed: %s", e)
            raise RuntimeError(
                f"Gemini HTTP failed to follow the deterministic contract: {e}"
            ) from e

    def generate_stream(
        self,
        messages: list[ChatMessage],
    ) -> Generator[str, None, None]:
        pass
