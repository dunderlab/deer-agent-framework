from deer import DeterministicAgent
from deer.cli import AgentREPL, get_path_from_parser, get_driver_from_parser
from deer.tools import ToolRegistry
from deer.tools.presets import Preset
from deer.tools.providers import HTTPClient, SystemObserver
from deer.drivers import OllamaDriver

from pathlib import Path


# Infrastructure
driver = get_driver_from_parser() or OllamaDriver(model_name="gemma4:31b-cloud")
registry = ToolRegistry(
    Preset.CODE_REPAIR
    | Preset.CODE_EDITOR
    | Preset.DATA_ANALYST
    | {HTTPClient, SystemObserver}
)
working_dir = get_path_from_parser() or Path.cwd()

PythonArchitectAgent = DeterministicAgent(
    description="AI specialist in Python architecture, runtime module resolution, and dependency management.",
    identity=(
        "You are an elite AI Agent operating as a Principal Python Architect and Core Ecosystem Specialist. "
        "You provide authoritative, deterministic guidance on advanced module resolution, runtime execution, "
        "dependency isolation, and package distribution. Your expertise spans the entire Python lifecycle: "
        "from engineering scalable code structures to resolving complex import mechanisms and optimizing "
        "deployment pipelines across public or internal repositories."
    ),
    driver=driver,
    tool_registry=registry,
    working_dir=working_dir,
    max_attempts=3,
)


def main():
    repl = AgentREPL(PythonArchitectAgent)
    repl.repl()


if __name__ == "__main__":
    main()
