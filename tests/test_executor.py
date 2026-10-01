import pytest
from deer.tools import ToolRegistry
from deer.tools.providers import LogicProvider
from deer.core.executor import PipelineExecutor
from deer.models import ExecutionPlan, ToolStep


@pytest.fixture
def tool_registry():
    tr = ToolRegistry()
    tr.register(LogicProvider())
    return tr


def test_executor(tool_registry):

    pipeline_executor = PipelineExecutor(tool_registry)

    execution_plan = ExecutionPlan(
        goal="",
        steps=[
            ToolStep(
                step_id="id-1",
                tool_name="evaluate",
                arguments={
                    "expression": "f'Hola {var}'.upper()",
                    "context": {"var": "mundo"},
                },
                reasoning="",
            )
        ],
        response="",
    )

    execution = pipeline_executor.execute(execution_plan)

    assert execution.steps, "The execution produced no steps"

    result = execution.steps[0].output["result"]
    assert result == "HOLA MUNDO", f"Expected 'HOLA MUNDO', got {result!r}"
