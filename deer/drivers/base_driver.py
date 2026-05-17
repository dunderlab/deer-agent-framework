from typing import Protocol, Type, TypeVar
from pydantic import BaseModel

# T represents any class inheriting from BaseModel
T = TypeVar("T", bound=BaseModel)


class LLMDriver(Protocol):
    """Contract for drivers supporting Architectural Brilliance."""

    def generate(self, prompt: str, response_model: Type[T]) -> T:
        """
        Takes a prompt and a Pydantic model.
        Returns a validated instance of that model.
        """
