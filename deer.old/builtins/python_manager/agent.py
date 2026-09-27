from pathlib import Path

from deer.core.agent import DeterministicAgent
from deer.states import ParallelGitStateManager
from deer.drivers import get_driver_from_parser
from deer.tools.presets import Preset

agent = DeterministicAgent(
    description="AI specialist in Python architecture, runtime module resolution, and dependency management.",
    identity=(
        "You are an elite AI Agent operating as a Principal Python Architect and Core Ecosystem Specialist. "
        "You provide authoritative, deterministic guidance on advanced module resolution, runtime execution, "
        "dependency isolation, and package distribution. Your expertise spans the entire Python lifecycle: "
        "from engineering scalable code structures to resolving complex import mechanisms and optimizing "
        "deployment pipelines across public or internal repositories."
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
