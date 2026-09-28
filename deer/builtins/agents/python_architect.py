from deer import DeterministicAgent
from deer.tools import Preset
from deer.evals import AgentREPL
from deer.parser import get_driver_from_parser

# from deer.drivers import OllamaDriver

from pathlib import Path

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
    # driver=OllamaDriver(model_name="gemma4:31b-cloud"),
    tool_registry=Preset.CODE_REPAIR | Preset.CODE_EDITOR | Preset.DATA_ANALYST,
    working_dir=Path.cwd(),
    max_attempts=3,
)


def main():
    repl = AgentREPL(agent)
    repl.repl()


if __name__ == "__main__":
    main()
