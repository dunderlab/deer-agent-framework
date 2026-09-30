from deer import DeterministicAgent

from deer.cli import AgentREPL, get_driver_from_parser, get_path_from_parser

from deer.tools import ToolRegistry, Preset
from deer.memory import VectorMemory
from deer.drivers import OllamaDriver

from pathlib import Path

# Infrastructure
driver = get_driver_from_parser() or OllamaDriver(model_name="gemma4:31b-cloud")
memory = VectorMemory(path=Path.home() / "deer_os_sandbox" / ".deer" / "vector_db")
registry = ToolRegistry(Preset.SYSTEM_ADMIN)
working_dir = get_path_from_parser() or Path.cwd()

agent = DeterministicAgent(
    description="OS Agent",
    identity=(
        "You are a capable Operating System Agent. "
        "Your goal is to assist the user by managing the system, executing tasks, and solving problems efficiently. "
        "You act as a direct interface to the OS, balancing helpfulness with a strict commitment to security: "
        "never perform destructive actions without confirmation and always stay within your designated boundaries."
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
