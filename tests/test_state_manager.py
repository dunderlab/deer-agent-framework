import os
from idlelib import history
from pathlib import Path

import pytest
from deer.drivers import OllamaKeyDriver
from deer.models import ChatMessage, Role
from deer import DeterministicAgent
from deer.tools import ToolRegistry
from deer.tools.presets import Preset
from deer.tools.providers import HTTPClient
from deer.memory import VectorMemory


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
        enable_verification=False,
        state_manager=True,
    )

    return agent


def test_rollback(agent):
    commit_hash_init = agent.state_manager.save_state("Initial state")

    commit_hash_first = agent.state_manager.save_state("Fist change")
    file_path = agent.working_dir_path / "test.txt"
    file_path.write_text("invierno")

    commit_hash_second = agent.state_manager.save_state("Second change")
    file_path.write_text("primavera")
    assert file_path.read_text() == "primavera"

    agent.restore_previous_state()
    assert file_path.read_text() == "invierno"
