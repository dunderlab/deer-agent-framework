import pytest
from deer.tools import ToolRegistry, Preset
from deer.drivers import OllamaDriver
from deer.planner import Planner


@pytest.fixture
def tool_registry():
    tr = ToolRegistry()
    tr.register(*[tool() for tool in Preset.ALL_TOOLS])
    return tr


@pytest.fixture
def driver():
    driver = OllamaDriver(model_name="gemma4:31b-cloud")
    return driver


def test_description(tool_registry, driver):

    planner = Planner(driver=driver, tool_registry=tool_registry)
    plan = planner.plan(
        goal='Genera un archivo llamado "juanita.py" con una función llamada "Leah" que no recibe argumentos.',
        context=[],
    )

    pass
