from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class ToolStep(BaseModel):
    """
    Represents a single atomic action in the execution pipeline.
    """

    step_id: str = Field(
        ...,
        description="Unique identifier for the step (e.g., 'step_1'). Used for referencing outputs in later steps.",
    )
    tool_name: str = Field(
        ..., description="The exact name of the tool to execute from the ToolRegistry."
    )
    arguments: Dict[str, Any] = Field(
        ...,
        description="The arguments for the tool. Use {{step_id.key}} to reference previous outputs.",
    )
    return_schema: Dict[str, str] = Field(
        ...,
        description="The expected return structure of the tool (e.g., {'result': 'bool'}).",
    )
    reasoning: str = Field(
        ...,
        description="Technical justification for why this tool is used in this specific sequence.",
    )


class ExecutionPlan(BaseModel):
    """
    A complete deterministic pipeline to achieve a specific goal.
    """

    goal: str = Field(
        ..., description="The original objective the agent is trying to solve."
    )

    steps: List[ToolStep] = Field(
        default_factory=list,
        description="The ordered sequence of tool calls to be executed linearly. Empty if no tools are needed.",
    )

    response: Optional[str] = Field(
        None,
        description="The final answer or reasoning provided by the model. This is used when no tool steps are required or to provide the final conclusion after steps are executed.",
    )


class StepTrace(BaseModel):
    """
    A record of a single tool execution.
    This is the 'forensic evidence' of what actually happened.
    """

    step_id: str
    tool_name: str
    resolved_args: Dict[str, Any]
    output: Any
    status: str  # "SUCCESS" or "FAILED"
    execution_time: float
    error: Optional[str] = None

    def __str__(self):
        if self.error:
            line = f"Error: {self.error}\n"
        else:
            line = ""
        return (
            f"Tool name: {self.tool_name}\n"
            f"Resolved args: {self.resolved_args}\n"
            f"Output: {self.output}\n"
            f"Status: {self.status}\n"
            f"Execution time: {self.execution_time}\n"
            f"{line}"
        )


class ExecutionTrace(BaseModel):
    """
    The complete history of a pipeline execution.
    """

    goal: str
    response: Optional[str]
    steps: list[StepTrace] = []
    overall_status: str = "PENDING"

    def __str__(self):
        return (
            "  -> ".join([step.tool_name for step in self.steps])
            + "\n\n"
            + "\n".join([str(step) for step in self.steps])
        )


class AgentConclusion(BaseModel):
    summary: str = Field(..., description="Professional summary of the results.")

    goal_achieved: bool = Field(
        ..., description="True if the goal was definitively achieved."
    )

    # Case 1: The tool worked, but the auditor failed (Technical glitch)
    needs_reverification: bool = Field(
        ...,
        description="True if the verification failed due to a technical error (e.g. malformed path) and should be retried.",
    )

    # Case 2: The goal was not met (Logical failure)
    needs_resolution: bool = Field(
        ...,
        description="True if the goal was not achieved and a new plan is required to fix the state of the system.",
    )

    confidence_score: float = Field(
        ..., description="Confidence in this verdict (0.0 to 1.0)."
    )

    user_message: str = Field(
        ...,
        description="A friendly, clear, and professional message for the end-user. "
        "Do NOT mention 'traces', 'JSON', 'steps', or 'tools'. "
        "Just explain what happened and the final result.",
    )
