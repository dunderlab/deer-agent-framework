from typing import Callable
from deer.schema.plan import Plan
from deer.tools.registry import ToolRegistry
from .rules import Rules

Rule = Callable[[Plan], None]


class PlanValidator:
    """Validador de planes que compone múltiples reglas.

    Uso:
        validator = PlanValidator(tool_registry)
        validator.validate(plan)
    """

    def __init__(self, tool_registry: ToolRegistry) -> None:
        self.tool_registry = tool_registry

    def validate(self, plan: Plan) -> None:

        rules = Rules(plan, self.tool_registry)
        rules.validate()
