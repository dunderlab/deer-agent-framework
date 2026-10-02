from rich.console import Console


class ConsoleColor:
    console = Console()

    @classmethod
    def on_info(cls, message: str):
        cls.console.print(f"[bold cyan]INFO[/bold cyan]  {message}")

    @classmethod
    def on_success(cls, message: str):
        # Verde para confirmaciones y tareas completadas
        cls.console.print(f"[bold green]SUCCESS[/bold green] {message}")

    @classmethod
    def on_warning(cls, message: str):
        # Amarillo para alertas que no detienen la ejecución
        cls.console.print(f"[bold yellow]WARNING[/bold yellow] {message}")

    @classmethod
    def on_error(cls, message: str):
        # Rojo para fallos críticos
        cls.console.print(f"[bold red]ERROR[/bold red] {message}")

    @classmethod
    def on_debug(cls, message: str):
        # Magenta o Gris para información técnica de desarrollo
        cls.console.print(f"[bold magenta]DEBUG[/bold magenta] {message}")

    @classmethod
    def on_system(cls, message: str):
        # Azul para mensajes internos del núcleo o del framework
        cls.console.print(f"[bold blue]SYSTEM[/bold blue] {message}")
