from pathlib import Path

import pytest
from deer.drivers import OllamaKeyDriver
from deer.models import ChatMessage, Role
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


def test_agent_response(agent):
    assert agent.format_bytes(2**15) == "32.0 kB"
    assert agent.format_bytes(10) == "10.0 B"


def test_agent_persist(agent):
    agent.persist_state()
    agent.restore_state()


def test_agent_trace(agent):
    agent.save_trace()
    # agent.save_trace_solution()
    # agent.save_trace_verification()


def test_agent_state(agent):
    agent.persist_state()
    agent.restore_state()


def test_agent_tools(agent):
    response = agent.run("Usa la tool `evaluate` para calcular cuanto es `2**16`")
    assert isinstance(response, str)
