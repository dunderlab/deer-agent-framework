import sys
import pickle
import logging
import subprocess

from rich.console import Console
from rich.markdown import Markdown
from prompt_toolkit import prompt
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.completion import Completer, WordCompleter

from deer.core import DeterministicAgent
from deer import __version__

logger = logging.getLogger(f"DEER.{__name__}")

COMMANDS = {
    "/tools": "Show tools and capabilities",
    "/clear": "Clear the console and reset the session",
    "/exit": "Terminate the session",
    "/rollback": "Revert the system to the last stable state",
    "/trace": "Display the detailed execution trace and variable resolution of the last plan.",
    "/context": "Displays context memory usage information.",
    "/history": "Display the history of messages and commands",
    "/vhistory": "Display the history of verifier messages and commands",
    "/loadcontext": "Restore a saved session context",
    "/savecontext": "Save the current session context",
}

WELCOME_MESSAGE = """
# DEER - Deterministic Executable Engine for Runtime Agents - v{version}

An LLM agent orchestration framework built for:  
- Strict runtime control
- Enforced tool contracts
- Full execution traceability
- Guaranteed reproducibility

## Runtime Pipeline

1. Plan      → Generate a structured execution strategy
2. Validate  → Verify contracts, dependencies, and safety
3. Execute   → Run approved tools and workflows
4. Verify    → Validate outputs against expected objectives

## System Guarantees

- Deterministic execution flow
- Typed tool interfaces
- Structured validation layers
- Full execution traceability
- Backend-governed orchestration

## Commands

{commands}

## System Escapes

- `!<command>` → Execute an OS shell command (e.g., `!ls -la` or `!pwd`)

## Shortcuts

- `Tab`        → Auto-complete commands and navigate suggestions
- `Ctrl+C`     → Stop processing the current task
"""


class SmartCommandCompleter(Completer):
    def __init__(self, commands):
        self.base_completer = WordCompleter(commands, ignore_case=False)

    def get_completions(self, document, complete_event):
        word_before_cursor = document.get_word_before_cursor()
        if not word_before_cursor:
            return []
        return self.base_completer.get_completions(document, complete_event)


class AgentREPL:

    def __init__(self, agent: DeterministicAgent):
        self.agent = agent

        self.prompt_history: InMemoryHistory
        self.load_prompt_history()

        self.console = Console()

    @property
    def completer(self):
        internal_commands = list(COMMANDS.keys())
        return SmartCommandCompleter(internal_commands)

    def load_prompt_history(self):
        history_file = self.agent.agent_dir / "prompt_history"

        if not history_file.exists():
            self.prompt_history = InMemoryHistory()
            return

        with open(history_file, "rb") as f:
            self.prompt_history = pickle.load(f)
        return

    def save_prompt_history(self):
        history_file = self.agent.agent_dir / "prompt_history"
        with open(history_file, "wb") as f:
            pickle.dump(self.prompt_history, f)

    def clear_history(self):
        self.history = []
        self.trace = []

    def pretty_print(self, out: str):
        self.console.print(Markdown(out))

    def show_welcome(self):
        commands_formated = ""
        for command in COMMANDS:
            commands_formated += (
                f"- {('`'+command+'`').ljust(12, ' ')} → {COMMANDS[command]}\n "
            )

        self.console.clear()
        self.pretty_print(
            WELCOME_MESSAGE.format(version=__version__, commands=commands_formated)
        )
        self.pretty_print(
            f">**Agent Profile**  \n"
            f"*{self.agent.description}*  \n"
            f"root: {self.agent.tool_registry.jail_path}  \n"
            f"{self.agent.driver}: {self.agent.driver.model_name}  \n"
        )
        print("\n")

    def run_command(self, command):
        match command:
            case "/exit":
                sys.exit(0)

            case "/clear":
                self.clear_history()
                self.console.clear()
                self.agent.clear_agent_history()
                self.agent.clear_traces()
                self.pretty_print(f">**Agent Profile**  \n*{self.agent.description}*")
                print("\n")

            case "/tools":
                self.pretty_print(self.agent.tool_registry.describe())
                print("\n")

            case "/rollback":
                self.pretty_print(
                    "**Rollback executed.** System reverted to the last stable state."
                )
                print("\n")

            case "/trace":
                trace = self.agent.traces["solution"]
                for i, step in enumerate(trace):
                    self.console.print(f"[bold yellow]Trace {i+1}:[/bold yellow]")
                    print(f"{step}")
                    print("\n")

            case "/history":
                for i, chat in enumerate(self.agent.agent_history[1:]):
                    self.console.print(f"[bold yellow]Chat {i+1}:[/bold yellow]")
                    print(f"{chat}")
                    print("\n")

            case "/vhistory":
                for i, chat in enumerate(self.agent.verificator_history[1:]):
                    self.console.print(f"[bold yellow]Chat {i+1}:[/bold yellow]")
                    print(f"{chat}")
                    print("\n")

            case "/context":
                bytes = sum(len(str(item)) for item in self.agent.agent_history)
                for unit in ["B", "KB", "MB", "GB", "TB"]:
                    if bytes < 1024.0:
                        size = f"{bytes:.1f} {unit}"
                        break
                    bytes /= 1024.0

                self.pretty_print(
                    f"  * **History:** {len(self.agent.agent_history)} messages\n"
                    f"  * **Context size:** ~{size}"
                )
                print("\n")

            case "/savecontext":
                self.agent.save_context()

            case "/loadcontext":
                self.agent.load_context()

    def repl(self):
        logger.setLevel(logging.CRITICAL)
        self.show_welcome()

        while True:
            try:
                msg = prompt(
                    HTML("<ansicyan><b>&gt;&gt;&gt; </b></ansicyan>"),
                    history=self.prompt_history,
                    completer=self.completer,
                    # multiline=True,
                )
                self.save_prompt_history()
                self.agent.save_context()
            except KeyboardInterrupt:
                continue
            except EOFError:
                break

            msg = msg.strip()
            if not msg:
                continue

            match msg:
                case command if command in COMMANDS:
                    self.run_command(command)

                case command if command.startswith("!"):
                    # Remove the '!' from the start to get only the command
                    cmd_to_run = command[1:].strip()

                    try:
                        # Execute the command
                        result = subprocess.run(
                            cmd_to_run,
                            shell=True,
                            capture_output=True,
                            text=True,
                            check=True,
                        )
                        print(result.stdout)
                    except subprocess.CalledProcessError as e:
                        print(f"Error executing command: {e.stderr}")
                    except Exception as e:
                        print(f"An unexpected error occurred: {e}")

                case _:
                    if msg.startswith("/"):
                        self.pretty_print(
                            f"Command `{msg}` not recognized. Did you mean one of these: {list(COMMANDS)}"
                        )
                        continue
                    with self.console.status(
                        "[dim]processing request[/]",
                        spinner="point",
                        spinner_style="dim",
                    ):
                        try:
                            output = self.send(msg)
                            self.pretty_print(f"    {output}")

                            print("\n")
                        except KeyboardInterrupt:
                            self.console.print("[dim]Command aborted by user[/]\n")
                            # self.state_restore()
                            continue
                        except EOFError:
                            break

    def send(self, message, print_chat: bool = False):

        if print_chat:
            print(f">>> {message}")

        response = self.agent.run(message)

        if print_chat:
            print(f"    {response}")

        return response
