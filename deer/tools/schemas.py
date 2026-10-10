from functools import lru_cache
import itertools
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, create_model, ConfigDict

_counter = itertools.count()


@dataclass(frozen=True)
class Case:
    args: dict[str, Any]
    expected: dict[str, Any] | None = None
    files: dict[str, str | bytes] = field(default_factory=dict)
    dirs: list[str] = field(default_factory=list)
    expected_paths: list[str] = field(default_factory=list)
    expected_json: dict[str, Any] = field(default_factory=dict)

    expected_yaml: dict[str, Any] = field(default_factory=dict)
    expected_contains: dict[str, list[str]] = field(default_factory=dict)
    expected_absent: dict[str, list[str]] = field(default_factory=dict)
    expected_toml: dict[str, Any] = field(default_factory=dict)

    raises: type[Exception] | None = None


class ReturnModel:
    """
    A factory class to dynamically create Pydantic models.

    This class allows for the creation of inline Pydantic models with
    specified fields, which is useful for generating dynamic schemas
    on the fly.

    Methods
    ----------
    __call__(fields)
        Creates and returns a new Pydantic BaseModel class with the
        provided fields.

    Parameters
    ----------
    fields : dict[str, Any]
        A dictionary where keys are field names and values are the
        corresponding types for those fields.

    Returns
    -------
    type[BaseModel]
        A dynamically created Pydantic model class.
    """

    def __call__(self, **fields: Any) -> type[BaseModel]:
        """
        Dynamically create a Pydantic model based on provided fields.

        Args:
            **fields: Field names and their respective types.

        Returns:
            A new Pydantic model class.
        """
        model_name = f"InlineModel_{next(_counter)}"

        # PSS: Transform fields into (type, ...) to mark them as required
        # while maintaining the Pydantic create_model signature.
        field_definitions = {
            name: (field_type, ...) for name, field_type in fields.items()
        }

        return create_model(
            model_name,
            **field_definitions,
            __config__=ConfigDict(arbitrary_types_allowed=True),
        )


Return = ReturnModel()
CommandOut = Return(stdout=str, stderr=str, returncode=int, message=str)
