from pathlib import Path

import pytest
from pydantic import ValidationError

from deer.drivers import OllamaKeyDriver
from deer import DeterministicAgent


@pytest.fixture
def agent(tmp_path):
    driver = OllamaKeyDriver(model_name="nemotron-3-nano:30b")

    agent = DeterministicAgent(
        description="Advanced OS Agent for secure system management.",
        identity=(
            "You are a capable Operating System Agent. "
            "Your goal is to assist the user by managing the system, executing tasks, and solving problems efficiently. "
            "You act as a direct interface to the OS, balancing helpfulness with a strict commitment to security: "
            "never perform destructive actions without confirmation and always stay within your designated boundaries."
        ),
        driver=driver,
        working_dir=Path(tmp_path),
        max_attempts=3,
        enable_verification=True,
    )

    return agent


def test_agent_response(agent):
    response = agent.run("Hola")
    assert isinstance(response, str)


def test_agent_tools(agent):
    response = agent.run("Usa la tool `evaluate` para calcular cuanto es `2**16`")
    assert isinstance(response, str)


def test_agent_tools_no_validate(agent):

    def fake_plan_validate(plan):
        plan.steps = plan.steps * 2
        return agent.plan_validator.validate_secure(plan)

    agent.plan_validator.validate_secure = agent.plan_validator.validate
    agent.plan_validator.validate = fake_plan_validate

    response = agent.run("Usa la tool `evaluate` para evaluar `lambda: 1`")
    assert isinstance(response, str)
