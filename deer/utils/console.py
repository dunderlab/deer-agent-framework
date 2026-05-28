from rich.console import Console

console = Console()


def info(message: str):
    console.print(f"[bold cyan]INFO[/bold cyan]  {message}")


def error(message: str):
    console.print(f"[bold red]ERROR[/bold red] {message}")
