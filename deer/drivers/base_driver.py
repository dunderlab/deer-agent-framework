from typing import Protocol, Type, TypeVar
from pydantic import BaseModel

# T represents any class inheriting from BaseModel
T = TypeVar("T", bound=BaseModel)


class LLMDriver(Protocol):
    """Contract for drivers supporting Architectural Brilliance."""

    def generate_text(self, prompt: str) -> str:
        """
        Generates text from the given prompt using the LLM driver.
        """
        pass

    def generate_json(self, prompt: str, response_model: Type[T] = None) -> T:
        """
        Generates JSON data from the given prompt using the LLM driver.
        If response_model is provided, returns a validated instance of that model.
        """
        pass

    def escape_logic(self, text: str) -> str:
        text = text.replace('"""', '\\"\\"\\"')
        return text
