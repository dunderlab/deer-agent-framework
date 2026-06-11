import subprocess
import sys

from rich.text import Text

from deer.builtins import agents
from deer.utils.console import console, error, info
from deer.drivers import drivers_parser


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


def main():
    args = drivers_parser.parse_args()

    title()

    if selected_agent := args.agent:
        if selected_agent in agents:
            info(f"Launching agent '{selected_agent}'")

            command = [
                sys.executable,
                agents[selected_agent],
            ]

            if args.backend:
                command.extend(["--backend", args.backend])

            if args.model:
                command.extend(["--model", args.model])

            result = subprocess.run(command)
            sys.exit(result.returncode)

        error(f"Unknown agent '{selected_agent}'")
        agents_list()
        sys.exit(1)

    error("No agent selected")
    example()
    agents_list()


if __name__ == "__main__":
    main()
