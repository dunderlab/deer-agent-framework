import itertools
from typing import Any, Optional, Dict
from pydantic import BaseModel, create_model

_counter = itertools.count()


def Return(**fields: Any) -> type[BaseModel]:
    return create_model(
        f"InlineModel_{next(_counter)}",
        **{name: (field_type, ...) for name, field_type in fields.items()},
    )


CommandOut = Return(stdout=str, stderr=str, returncode=int, message=str)
