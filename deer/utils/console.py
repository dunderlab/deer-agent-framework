from rich.console import Console

console = Console()


def info(message: str):
    console.print(f"[bold cyan]INFO[/bold cyan]  {message}")


def success(message: str):
    # Verde para confirmaciones y tareas completadas
    console.print(f"[bold green]SUCCESS[/bold green] {message}")


def warning(message: str):
    # Amarillo para alertas que no detienen la ejecución
    console.print(f"[bold yellow]WARNING[/bold yellow] {message}")


def error(message: str):
    # Rojo para fallos críticos
    console.print(f"[bold red]ERROR[/bold red] {message}")


def debug(message: str):
    # Magenta o Gris para información técnica de desarrollo
    console.print(f"[bold magenta]DEBUG[/bold magenta] {message}")


def system(message: str):
    # Azul para mensajes internos del núcleo o del framework
    console.print(f"[bold blue]SYSTEM[/bold blue] {message}")
