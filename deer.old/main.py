import sys
import importlib.util
from rich.text import Text
import logging

from deer.builtins import agents
from deer.utils.console import console, error, info
from deer.drivers import drivers_parser

logger = logging.getLogger("DEER")


def title():
    console.print()
    console.print(
        Text(
            "DEER",
            style="bold cyan",
        )
    )
    console.print(
        "Deterministic Executable Engine for Runtime Agents",
        style="dim",
    )
    console.print()


def agents_list():
    console.print()
    console.print("[bold]Available agents[/bold]")
    for name in agents:
        console.print(f"  • [green]{name}[/green]")
    console.print()


def example():
    console.print(f"[dim]Example:[/dim] deer {agents[0]}")


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


def main():
    args = drivers_parser.parse_args()

    title()

    if selected_agent := args.agent:

        if selected_agent in agents:
            info(f"Launching agent '{selected_agent}'")
            run_agent_in_process(agents[selected_agent], args.backend, args.model)
            sys.exit(0)

        error(f"Unknown agent '{selected_agent}'")
        agents_list()
        sys.exit(1)

    error("No agent selected")
    example()
    agents_list()


if __name__ == "__main__":
    main()
