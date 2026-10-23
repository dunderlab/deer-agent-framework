from pathlib import Path

from deer import DeterministicAgent
from deer.cli import AgentREPL, get_path_from_parser, get_driver_from_parser

# Infrastructure
driver = get_driver_from_parser()
working_dir = get_path_from_parser() or Path.cwd()

agent = DeterministicAgent(
    description="Base Agent",
    identity="",
    driver=driver,
    working_dir=working_dir,
    max_attempts=1,
    enable_verification=False,
)


def main():
    repl = AgentREPL(agent)
    repl.repl()


if __name__ == "__main__":
    main()
