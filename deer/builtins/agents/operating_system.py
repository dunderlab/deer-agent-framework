from deer import DeterministicAgent

from deer.evals import AgentREPL
from deer.parser import get_driver_from_parser, get_path_from_parser

from deer.tools import ToolRegistry, Preset
from deer.core import VectorMemory
from deer.drivers import OllamaDriver

from pathlib import Path

# Infrastructure
driver = get_driver_from_parser() or OllamaDriver(model_name="gemma4:31b-cloud")
memory = VectorMemory(path=Path.home() / "deer_os_sandbox" / ".deer" / "vector_db")
registry = ToolRegistry(Preset.SYSTEM_ADMIN)
working_dir = get_path_from_parser() or Path.cwd()

agent = DeterministicAgent(
    description="Natural Language to OS Translator",
    identity=(
        "You are an Operating System Automation Specialist. "
        "Your function is to translate user requests into precise system operations. "
        "You prioritize security: never perform destructive actions without confirmation "
        "and stay strictly within the boundaries of your Jail."
    ),
    driver=driver,
    tool_registry=registry,
    vector_memory=memory,
    working_dir=working_dir,
    max_attempts=3,
    enable_verification=False,
)


def main():
    repl = AgentREPL(agent)
    repl.repl()


if __name__ == "__main__":
    main()
