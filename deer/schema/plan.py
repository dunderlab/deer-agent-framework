from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator, model_validator


class Step(BaseModel):

    id: str = Field(..., description="Unique step identifier (e.g., s1, s2)")

    tool: Optional[str] = Field(
        None, description="Name of the tool to invoke. Optional if 'logic' is provided."
    )

    logic: Optional[str] = Field(
        None,
        description="Restricted Python expression executed by the deterministic runtime.",
    )

    input_from: Optional[str] = Field(
        None,
        description="ID of the previous step whose output will be passed as input.",
    )

    params: Dict[str, Any] = Field(
        default_factory=dict,
        description="Literal parameters or configuration for the tool/logic.",
    )

    @model_validator(mode="before")
    @classmethod
    def _normalize_string_nulls(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        for field_name in ("tool", "logic", "input_from"):
            if data.get(field_name) == "null":
                data[field_name] = None

        return data

    @field_validator("id")
    @classmethod
    def _non_empty_id(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Step.id cannot be empty")
        return v

    @model_validator(mode="after")
    def _validate_action(self) -> "Step":
        has_tool = bool(self.tool and self.tool.strip())
        has_logic = bool(self.logic and self.logic.strip())

        if has_tool == has_logic:
            raise ValueError("A step must provide exactly one of 'tool' or 'logic'.")

        return self


class Plan(BaseModel):

    steps: List[Step] = Field(
        default_factory=list,
        description="Ordered sequence of steps to be executed by the orchestrator.",
    )

    def step_by_id(self, step_id: str) -> Step:
        for s in self.steps:
            if s.id == step_id:
                return s
        raise KeyError(f"Step not found: {step_id}")
