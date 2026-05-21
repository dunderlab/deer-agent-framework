import itertools
from typing import Any, Dict, Optional, List
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


class Trace(BaseModel):
    steps: List[StepTrace] = Field(default_factory=list)


class AgentOutput(BaseModel):
    result: Any = None
    trace: List[StepTrace] = Field(default_factory=list)
    validated: bool = (False,)
    # image: Optional[str] = None

    def text(self):
        return f"{str(self.result)}"


def Struct(**fields: Any) -> type[BaseModel]:
    return create_model(
        f"InlineModel_{next(_counter)}",
        **{name: (field_type, ...) for name, field_type in fields.items()},
    )
