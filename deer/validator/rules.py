from typing import Set
import inspect
import logging

from deer.schema.plan import Plan
from deer.tools.registry import ToolRegistry


class Rules:
    """Mandatory validation rules for NOMOS executable plans."""

    def __init__(self, plan: Plan, registry: ToolRegistry) -> None:
        self.plan = plan
        self.registry = registry

    def validate(self) -> None:
        """Dynamically discovers and executes all methods prefixed with 'check_'."""
        checkers = inspect.getmembers(self, predicate=inspect.ismethod)
        for name, method in checkers:
            if name.startswith("check_"):
                logging.info(f"Validating rule: {name}")
                # Ensure the method receives the plan for validation
                method(self.plan)

    def check_unique_step_ids(self, plan: Plan) -> None:
        seen: Set[str] = set()
        for s in plan.steps:
            if s.id in seen:
                raise ValueError(f"Duplicate step IDs detected: {s.id}")
            seen.add(s.id)

    def check_existing_references(self, plan: Plan) -> None:
        ids = {s.id for s in plan.steps}
        for s in plan.steps:
            if s.input_from is not None and s.input_from not in ids:
                raise ValueError(
                    f"Step '{s.id}' references an unknown input_from: {s.input_from}"
                )

    def check_topological_order(self, plan: Plan) -> None:
        """Ensures that input_from (if present) appears earlier in the sequence (preventing cycles/forward references)."""
        index = {s.id: i for i, s in enumerate(plan.steps)}
        for s in plan.steps:
            if s.input_from is None:
                continue
            if index[s.input_from] >= index[s.id]:
                raise ValueError(
                    f"Invalid execution order: '{s.id}' depends on '{s.input_from}', which has not been executed yet"
                )

    def check_tools_registered(self, plan: Plan) -> None:
        for s in plan.steps:
            if s.tool and not self.registry.has(s.tool):
                raise ValueError(f"Tool not found in ToolRegistry: {s.tool}")
