import logging
import shutil
import os
import sys

sys.path.append("../../")

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
# logger.setLevel(logging.CRITICAL)


def rollback():
    shutil.rmtree("/Users/yeison/Development/deer-agent-framework/sandbox/root")
    os.mkdir("/Users/yeison/Development/deer-agent-framework/sandbox/root")


# driver = GeminiDriver(model_name="gemini-3.1-flash-lite")
# driver = GeminiDriver(model_name="gemini-1.5-flash-lite")
driver = OllamaDriver(model_name="gemma4:31b-cloud")
agent = DeterministicAgent(
    description="Python Architecture Specialist expert in module lifecycle, dependency management, and package distribution.",
    identity=(
        "You are a Principal Python Architect and Core Ecosystem Specialist. You possess authoritative expertise "
        "in advanced module resolution, dependency management architectures, package distribution, and internal "
        "or public repository management. Your knowledge spans the entire lifecycle of Python code: from how "
        "modules are imported and structured at runtime, to how dependencies are resolved, isolated, packaged, "
        "and deployed across diverse environments."
    ),
    driver=driver,
    registry=registry,
    format_response="markdown",
    max_tries_for_plan=5,
    rollback=rollback,
)

agent.repl()
# agent.send("Hola")
# agent.iterate_debug([*PYTHON_PROJECT_PROMPT], repetitions=50, path="traces/python_project4")
