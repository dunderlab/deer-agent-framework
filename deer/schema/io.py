import itertools
from typing import Any, Dict, Optional, List, TypedDict
from pydantic import BaseModel, Field, create_model

_counter = itertools.count()


class AgentInput(BaseModel):
    goal: str = Field(..., description="Goal or task to fulfill")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Initial data")


class StepTrace(BaseModel):
    step_id: str
    tool: str
    input: Any
    output: Any
    error: Optional[str] = None


class AgentOutput(BaseModel):
    result: Any = None
    trace: List[StepTrace] = Field(default_factory=list)


def Struct(**fields: Any) -> type[BaseModel]:
    return create_model(
        f"InlineModel_{next(_counter)}",
        **{name: (field_type, ...) for name, field_type in fields.items()},
    )


# def Struct(**fields: Any) -> type[BaseModel]:
#     return TypedDict(f"InlineModel_{next(_counter)}", fields)
