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


def Return(**fields: Any) -> type[BaseModel]:
    return create_model(
        f"InlineModel_{next(_counter)}",
        **{name: (field_type, ...) for name, field_type in fields.items()},
        __config__=ConfigDict(arbitrary_types_allowed=True),
    )


CommandOut = Return(stdout=str, stderr=str, returncode=int, message=str)
