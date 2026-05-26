import logging
from datetime import datetime
import shutil
import os

from deer.core.agent import DeterministicAgent
from deer.drivers import GeminiDriver, OllamaDriver
from prompts import (
    SIMPLE_FILE_CREATION_PROMPT,
    PYTHON_PROJECT_PROMPT,
    SEQUENTIAL_FILE_EDITION_PROMPT,
)

from tools import registry
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("DEER")
logger.setLevel(logging.DEBUG)


def rollback():
    shutil.rmtree("sandbox/root")
    os.mkdir("sandbox/root")


# driver = GeminiDriver(model_name="gemini-3.1-flash-lite")
# driver = GeminiDriver(model_name="gemini-1.5-flash-lite")
# driver = OllamaDriver(model_name="qwen2.5-coder:7b")
# driver = OllamaDriver(model_name="qwen3.5:9b")
driver = OllamaDriver(model_name="gemma4:31b-cloud")
agent = DeterministicAgent(
    identity="You are a senior Python packaging and environment management specialist with deep expertise in"
    "pyproject.toml, dependency management, reproducible environments, build systems, virtual environments, "
    "and modern Python tooling ecosystems including pip, setuptools, pytest",
    driver=driver,
    registry=registry,
    format_response="markdown",
    max_tries_for_plan=5,
    rollback=rollback,
)
# agent.repl()


if __name__ == "__main__":
    chain_messages = [*PYTHON_PROJECT_PROMPT]

    for i in range(1):
        agent.clear_history()
        agent.rollback()

        name = f"{driver.model_name}-{datetime.now().timestamp()}"

        agent.generate_chat_log(
            chain_messages,
            print_chat=True,
            save_log=f"traces/python_project3/{name}.log",
        )
        agent.save_trace(f"traces/python_project3/{name}.trace")
