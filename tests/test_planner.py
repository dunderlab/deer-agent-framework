import pytest
from deer.tools import ToolRegistry
from deer.tools.providers import FileManager
from deer.drivers import OllamaDriver

from deer.core.planner import Planner, Role, ChatMessage
from deer.core.validator import PlanValidator


@pytest.fixture
def tool_registry():
    tr = ToolRegistry()
    tr.register(FileManager())
    return tr


@pytest.fixture
def driver():
    driver = OllamaDriver(model_name="gemma4:31b-cloud")
    return driver


def test_planer(tool_registry, driver):
    planner = Planner(identity="", dirver=driver, tool_registry=tool_registry)
    validator = PlanValidator(tool_registry=tool_registry)

    history = [
        ChatMessage(
            role=Role.SYSTEM,
            content=planner.build_system_prompt(),
        )
    ]

    plan, history = planner.plan(
        goal='Generate a file named "test.py" with a function called "function" that takes no arguments.',
        context=[],
        history=history,
    )

    validated, validated_info = validator.validate(plan)

    assert validated, f"The plan failed validation: {validated_info}"
    assert len(plan.steps) == 1, f"Expected 1 step, got {len(plan.steps)}"
    assert (
        plan.steps[0].tool_name == "new_file"
    ), f"Expected tool 'new_file', got '{plan.steps[0].tool_name}'"
