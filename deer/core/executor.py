import logging
import time
from typing import Any, Dict
from deer.tools import ToolRegistry
from deer.models import ExecutionPlan, ExecutionTrace, StepTrace

logger = logging.getLogger(f"DEER.{__name__}")


class PipelineExecutor:
    """
    The Execution Engine of DEER.
    Takes a validated ExecutionPlan and runs it step-by-step,
    resolving dynamic references and managing the execution state.
    """

    def __init__(self, tool_registry: ToolRegistry):
        self.tool_registry = tool_registry
        self.execution_context: Dict[str, Any] = {}

    def execute(self, plan: ExecutionPlan) -> ExecutionTrace:
        """
        Executes the plan and returns a full ExecutionTrace.
        """
        logger.info(f"Executing pipeline for goal: {plan.goal}")
        self.execution_context = {}

        trace = ExecutionTrace(goal=plan.goal, response=plan.response)

        try:
            for step in plan.steps:
                # 1. Resolve variables from context
                resolved_args = self._resolve_arguments(step.arguments)

                # 2. Fetch the tool
                tool = self.tool_registry.get(step.tool_name)

                # 3. Execute and measure
                start_time = time.perf_counter()
                try:
                    result = tool.run(params=resolved_args)

                    if result.get("returncode", 0):
                        status = "FAILED"
                    else:
                        status = "SUCCESS"

                    error_msg = None
                except Exception as e:
                    result = None
                    status = "FAILED"
                    error_msg = str(e)

                duration = time.perf_counter() - start_time

                # 4. Store result in context for future steps
                if result is not None:
                    self.execution_context[step.step_id] = result

                # 5. RECORD THE TRACE: This is the most important part
                trace.steps.append(
                    StepTrace(
                        step_id=step.step_id,
                        tool_name=step.tool_name,
                        resolved_args=resolved_args,
                        output=result,
                        status=status,
                        execution_time=duration,
                        error=error_msg,
                    )
                )

                # If a step fails, we stop the pipeline immediately (Deterministic failure)
                if status == "FAILED":
                    trace.overall_status = "FAILED"
                    return trace

            trace.overall_status = "COMPLETED"
            return trace

        except Exception as e:
            trace.overall_status = "CRASHED"
            logger.error(f"Critical Executor Crash: {e}")
            return trace

    def _resolve_arguments(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recursively searches for {{step_id.key}} patterns and replaces them
        with actual values from the execution_context.
        """
        resolved = {}
        for key, value in args.items():
            if isinstance(value, str) and "{{" in value and "}}" in value:
                resolved[key] = self._resolve_value(value)
            else:
                resolved[key] = value
        return resolved

    def _resolve_value(self, value: str) -> Any:
        """
        Parses a reference like '{{read_conf.content}}' and fetches the value.
        """
        # Extract the content between {{ and }}
        import re

        match = re.search(r"\{\{(.*?)\}\}", value)
        if not match:
            return value  # Not a reference, return as is

        path = match.group(1)  # e.g., "read_conf.content"

        if "." not in path:
            # Reference to the whole step output: {{step_id}}
            result = self.execution_context.get(path)
        else:
            # Reference to a specific key: {{step_id.key}}
            step_id, key = path.split(".", 1)
            step_result = self.execution_context.get(step_id)

            if step_result is None or not isinstance(step_result, dict):
                raise KeyError(
                    f"Step {step_id} not found or did not return a dictionary."
                )

            result = step_result.get(key)
            if result is None:
                raise KeyError(f"Key {key} not found in output of step {step_id}.")

        if result is None:
            raise KeyError(f"Reference {path} could not be resolved.")

        return result

    def _get_final_result(self, final_step_id: str) -> Any:
        """Extracts the final result of the pipeline."""
        if final_step_id not in self.execution_context:
            raise KeyError(f"Final step {final_step_id} was never executed.")
        return self.execution_context[final_step_id]
