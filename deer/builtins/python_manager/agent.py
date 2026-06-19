from pathlib import Path

from deer.core.agent import DeterministicAgent
from deer.states import ParallelGitStateManager
from deer.drivers import get_driver_from_parser
from deer.tools import Preset

agent = DeterministicAgent(
    description="Python Architecture Specialist expert in module lifecycle, dependency management, and package distribution.",
    identity=(
        "You are a Principal Python Architect and Core Ecosystem Specialist. You possess authoritative expertise "
        "in advanced module resolution, dependency management architectures, package distribution, and internal "
        "or public repository management. Your knowledge spans the entire lifecycle of Python code: from how "
        "modules are imported and structured at runtime, to how dependencies are resolved, isolated, packaged, "
        "and deployed across diverse environments."
    ),
    driver=get_driver_from_parser(),
    tool_registry=Preset.CODE_REPAIR | Preset.CODE_EDITOR | Preset.DATA_ANALYST,
    jail_path=Path.cwd(),
    format_response="markdown",
    max_retries=5,
    state_manager=ParallelGitStateManager(),
)


def main():
    agent.repl()


if __name__ == "__main__":
    main()
