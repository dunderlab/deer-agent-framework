from abc import ABC, abstractmethod
from typing import Any, Type
from dataclasses import dataclass, field

from pydantic import BaseModel


@dataclass
class ToolProvider:
    tools: list[str] | None = field(default=None, kw_only=True)


class Tool(ABC):
    """Base contract for deterministic tools."""

    # input_schema: Type[Any] | None = None
    # output_schema: Type[Any] | None = None
    #
    # name: str = ""
    # description: str = ""
    # modifies_state: bool = False

    def __init__(self) -> None:
        if not self.name:
            self.name = self.__class__.__name__.lower()

    def validate_input(self, value: Any) -> Any:
        return self._validate_with_schema(self.params_type, value)

    def validate_output(self, value: Any) -> Any:
        return self._validate_with_schema(self.return_type, value)

    def _validate_with_schema(self, schema: Type[Any] | None, value: Any) -> Any:
        if schema is None:
            return value

        if isinstance(schema, type) and issubclass(schema, BaseModel):
            return schema.model_validate(value)

        return value

    @abstractmethod
    def run(self, params: dict[str, Any] | None = None) -> Any:
        """Execute the tool deterministically.

        Args:
            value: Main input value.
            params: Optional literal parameters.

        Returns:
            The deterministic output produced by the tool.
        """
        raise NotImplementedError
