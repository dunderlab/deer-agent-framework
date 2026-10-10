from pathlib import Path

from deer import DeterministicAgent
from deer.cli import AgentREPL, get_path_from_parser, get_driver_from_parser
from deer.tools import ToolRegistry
from deer.tools.presets import Preset
from deer.tools.providers import HTTPClient
from deer.drivers import OllamaDriver

# Infrastructure
driver = get_driver_from_parser() or OllamaDriver(model_name="gemma4:31b-cloud")
registry = ToolRegistry(Preset.SYSTEM_ADMIN | {HTTPClient})
working_dir = get_path_from_parser() or Path.cwd()

agent = DeterministicAgent(
    description="Advanced OS Agent for secure system management.",
    identity=(
        "You are a capable Operating System Agent. "
        "Your goal is to assist the user by managing the system, executing tasks, and solving problems efficiently. "
        "You act as a direct interface to the OS, balancing helpfulness with a strict commitment to security: "
        "never perform destructive actions without confirmation and always stay within your designated boundaries."
    ),
    driver=driver,
    tool_registry=registry,
    working_dir=working_dir,
    max_attempts=3,
    enable_verification=False,
)


def main():
    repl = AgentREPL(agent)
    repl.repl()


if __name__ == "__main__":
    main()
