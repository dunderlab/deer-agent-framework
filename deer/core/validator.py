import re
from pickle import FALSE
from typing import Set
import inspect
import logging

from deer.tools.registry import ToolRegistry
from deer.models import ExecutionPlan

logger = logging.getLogger(f"DEER.{__name__}")


class Rules:
    """Mandatory validation rules for NOMOS executable plans."""

    def __init__(self, plan: ExecutionPlan, tool_registry: ToolRegistry) -> None:
        self.plan = plan
        self.tool_registry = tool_registry

    def validate(self) -> None:
        """Dynamically discovers and executes all methods prefixed with 'check_'."""
        checkers = inspect.getmembers(self, predicate=inspect.ismethod)
        for name, method in checkers:
            if name.startswith("check_"):
                logger.debug(f"Validating rule: {name}")
                method(self.plan)

    def check_unique_step_ids(self, plan: ExecutionPlan) -> None:
        seen: Set[str] = set()
        for s in plan.steps:
            if s.step_id in seen:
                raise ValueError(f"Duplicate step IDs detected: {s.step_id}")
            seen.add(s.step_id)

    def check_tools_registered(self, plan: ExecutionPlan) -> None:
        for s in plan.steps:
            if not self.tool_registry.has(s.tool_name):
                raise ValueError(f"Tool not found in ToolRegistry: {s.tool_name}")

    def check_tools_registered_params(self, plan: ExecutionPlan) -> None:
        """Ensures tool steps provide exactly the parameters declared by the tool."""
        for s in plan.steps:
            tool = self.tool_registry.get(s.tool_name)

            # Use the params_model we created in the ToolRegistry/Decorator
            if not hasattr(tool, "params_model"):
                continue

            expected_params = set(tool.params_model.model_fields.keys())
            provided_params = set(s.arguments.keys())

            missing = expected_params - provided_params
            if missing:
                raise ValueError(
                    f"Step '{s.step_id}' is missing required params for tool "
                    f"'{s.tool_name}': {', '.join(sorted(missing))}"
                )

            unknown = provided_params - expected_params
            if unknown:
                raise ValueError(
                    f"Step '{s.step_id}' provides unknown params for tool "
                    f"'{s.tool_name}': {', '.join(sorted(unknown))}"
                )

    def check_reference_integrity(self, plan: ExecutionPlan) -> None:
        """
        EnsPures that all {{step_id.key}} references:
        1. Point to a step that exists.
        2. Point to a step that was executed BEFORE the current step.
        3. Point to a key that exists in that step's return_schema.
        """
        # Map of step_id -> return_schema
        known_outputs = {}

        for s in plan.steps:
            # 1. Check references in the arguments of the current step
            for arg_name, arg_value in s.arguments.items():
                if isinstance(arg_value, str) and "{{" in arg_value:
                    # Extract the reference (e.g., 'read_conf.content' from '{{read_conf.content}}')
                    match = re.search(r"\{\{(.*?)\}\}", arg_value)
                    if match:
                        ref_path = match.group(1)
                        if "." not in ref_path:
                            raise ValueError(
                                f"Invalid reference in step '{s.step_id}': "
                                f"'{ref_path}' must follow the 'step_id.key' format."
                            )

                        ref_id, ref_key = ref_path.split(".", 1)

                        # A: Check if the referenced step exists AND was defined before this one
                        if ref_id not in known_outputs:
                            raise ValueError(
                                f"Reference Error in step '{s.step_id}': "
                                f"'{ref_id}' is unknown or referenced before it was created."
                            )

                        # B: Check if the key exists in that tool's return_schema
                        schema = known_outputs[ref_id]
                        if ref_key not in schema:
                            raise ValueError(
                                f"Type Error in step '{s.step_id}': "
                                f"The tool in '{ref_id}' does not return a key called '{ref_key}'."
                                f" Available keys: {list(schema.keys())}"
                            )

            # 2. After validating the current step, add its output schema to the known_outputs
            # This ensures a step cannot reference itself or a future step.
            known_outputs[s.step_id] = self._output_keys(s.tool_name)

    def _output_keys(self, tool_name: str) -> set[str]:
        tool = self.tool_registry.get(tool_name)
        return set(tool.return_type)


class PlanValidator:
    """Validador de planes que compone múltiples reglas.

    Uso:
        validator = PlanValidator(tool_registry)
        validator.validate(plan)
    """

    def __init__(self, tool_registry: ToolRegistry) -> None:
        self.tool_registry = tool_registry

    def validate(self, plan: ExecutionPlan) -> [bool, str]:
        rules = Rules(plan, self.tool_registry)

        try:
            rules.validate()
            return True, ""
        except Exception as e:
            return False, e
