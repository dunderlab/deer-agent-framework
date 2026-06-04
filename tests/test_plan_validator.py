import pytest
from pathlib import Path

from deer.schema.plan import Plan
from deer.tools.builtin.file_manager import FileManager
from deer.tools.registry import ToolRegistry
from deer.validator.plan_validator import PlanValidator

@pytest.fixture
def validator(tmp_path):
    tool_registry = ToolRegistry()
    file_manager = FileManager()
    file_manager.jail = tmp_path
    tool_registry.register(file_manager)
    return PlanValidator(tool_registry)

def test_rejects_missing_required_tool_params(validator):
    plan = Plan(
        steps=[
            {
                "id": "s1",
                "tool": "new_file",
                "logic": None,
                "input_from": None,
                "params": {},
            }
        ]
    )

    with pytest.raises(ValueError, match="missing required params"):
        validator.validate(plan)

def test_rejects_unknown_tool_params(validator):
    plan = Plan(
        steps=[
            {
                "id": "s1",
                "tool": "read_file",
                "logic": None,
                "input_from": None,
                "params": {"path": "example.py", "extra": True},
            }
        ]
    )

    with pytest.raises(ValueError, match="unknown params"):
        validator.validate(plan)

def test_accepts_declared_tool_params(validator):
    plan = Plan(
        steps=[
            {
                "id": "s1",
                "tool": "new_file",
                "logic": None,
                "input_from": None,
                "params": {"path": "example.py", "content": "input"},
            }
        ]
    )

    validator.validate(plan)
