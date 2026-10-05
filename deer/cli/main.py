import importlib.util
import logging
import sys

from rich.text import Text

from deer.utils.console import ConsoleColor
from deer.builtins_agents import agents

from .parser import drivers_parser

logger = logging.getLogger(f"DEER.{__name__}")


def title():
    ConsoleColor.console.print()
    ConsoleColor.console.print(
        Text(
            "DEER",
            style="bold cyan",
        )
    )
    ConsoleColor.console.print(
        "Deterministic Executable Engine for Runtime Agents",
        style="dim",
    )
    ConsoleColor.console.print()


def agents_list():
    ConsoleColor.console.print()
    ConsoleColor.console.print("[bold]Available agents[/bold]")
    for name in agents:
        ConsoleColor.console.print(f"  • [green]{name}[/green]")
    ConsoleColor.console.print()


def example():
    ConsoleColor.console.print(f"[dim]Example:[/dim] deer {list(agents.keys())[0]}")


def run_agent_in_process(agent_path, backend=None, model=None):
    command_args = [agent_path]

    if backend:
        command_args.extend(["--backend", backend])
    if model:
        command_args.extend(["--model", model])

    spec = importlib.util.spec_from_file_location("agent_module", agent_path)
    agent_module = importlib.util.module_from_spec(spec)

    sys.argv = command_args

    spec.loader.exec_module(agent_module)
    if hasattr(agent_module, "main"):
        return agent_module.main()
    else:
        logger.error("Agent does not have a 'main' function to run.")
        sys.exit(0)


def main():
    args = drivers_parser.parse_args()

    title()

    if selected_agent := args.agent:

        if selected_agent in agents:
            ConsoleColor.on_info(f"Launching agent '{selected_agent}'")
            run_agent_in_process(agents[selected_agent], args.backend, args.model)
            sys.exit(0)

        ConsoleColor.on_error(f"Unknown agent '{selected_agent}'")
        agents_list()
        sys.exit(1)

    ConsoleColor.on_error("No agent selected")
    example()
    agents_list()


if __name__ == "__main__":
    main()
