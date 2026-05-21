from typing import Callable
from deer.schema.plan import Plan
from deer.tools.registry import ToolRegistry
from .rules import Rules

Rule = Callable[[Plan], None]


class PlanValidator:
    """Validador de planes que compone múltiples reglas.

    Uso:
        validator = PlanValidator(registry)
        validator.validate(plan)
    """

    def __init__(self, registry: ToolRegistry) -> None:
        self.registry = registry

    def validate(self, plan: Plan) -> None:

        rules = Rules(plan, self.registry)
        rules.validate()
