import sys
import pickle
import logging
import subprocess

from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table
from rich.live import Live
from rich.text import Text
from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.completion import Completer, WordCompleter

from deer.core import DeterministicAgent
from deer import version_info

logger = logging.getLogger(f"DEER.{__name__}")

COMMANDS = {
    "/tools": "Show tools and capabilities.",
    "/clear": "Clear the console.",
    "/exit": "Terminate the session.",
    "/rollback": "Revert the system to the last stable state",
    "/trace": "Display the detailed execution trace and variable resolution of recent plans.",
    "/savetrace": "Saves the current execution trace to a file for later analysis.",
    "/history": "Display the history of messages and commands.",
    "/clearhistory": "Purge all session history and reset memory state.",
    # "/vhistory": "Display the history of verifier messages and commands",
    "/infocontext": "Displays context memory usage information.",
    "/loadcontext": "Restore a saved session context.",
    "/savecontext": "Save the current session context.",
    "/infoknowledge": "Displays total document count and storage usage.",
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

- `!<command>`  → Execute an OS shell command (e.g., `!ls -la` or `!pwd`)
- `? <message>` → Use the model as simple chat without context generation

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

        self.history = []
        self.trace = []

    @property
    def completer(self):
        internal_commands = list(COMMANDS.keys())
        return SmartCommandCompleter(internal_commands)

    def load_prompt_history(self):
        history_file = self.agent.agent_dir_path / "prompt_history"

        if not history_file.exists():
            self.prompt_history = InMemoryHistory()
            self.save_prompt_history()
            return

        with open(history_file, "rb") as f:
            self.prompt_history = pickle.load(f)
        return

    def save_prompt_history(self):
        history_file = self.agent.agent_dir_path / "prompt_history"
        with open(history_file, "wb") as f:
            pickle.dump(self.prompt_history, f)

    def clear_history(self):
        self.history = []
        self.trace = []

    def pretty_print(self, out: str):
        self.console.print(Markdown(out))

    def show_identity(self):
        self.pretty_print(
            f">**Agent Profile**  \n"
            f"*{self.agent.description}*  \n"
            f"root: {self.agent.tool_registry.jail_path}  \n"
            f"{self.agent.driver}  \n"
        )
        print("")

    def show_welcome(self):
        commands_formated = ""
        max_command = max(len(cm) for cm in COMMANDS) + 2
        for command, desc in COMMANDS.items():
            commands_formated += (
                f"- {('`'+command+'`').ljust(max_command, ' ')} → {desc}\n "
            )

        self.console.clear()
        self.pretty_print(
            WELCOME_MESSAGE.format(version=version_info, commands=commands_formated)
        )
        self.show_identity()

    def run_command(self, command, args):
        match command:
            case "/exit":
                self.agent.dump_history()
                self.console.print(
                    "[dim]Context state persisted to disk.[/dim]\n",
                    Markdown("----"),
                )
                sys.exit(0)

            case "/clear":
                self.console.clear()
                self.show_identity()
                self.console.print(
                    "[dim]Console buffer cleared. Session state persists. Use /clearhistory for a full purge.[/dim]\n",
                )

            case "/clearhistory":
                self.clear_history()
                self.console.clear()
                self.agent.reset_history()
                self.agent.reset_traces()
                self.agent.dump_history()
                self.show_identity()
                if unload_model := getattr(self.agent.driver, "unload_model"):
                    unload_model()
                self.console.print(
                    "[dim]Session history purged. Memory state reset.[/dim]\n",
                )

            case "/tools":
                tools_description = self.agent.tool_registry.describe()
                self.console.print(
                    Markdown(tools_description),
                    "\n",
                    f"[dim]Tool registry: {len(self.agent.tool_registry.tools)} modules active.[/dim]\n",
                    f"[dim]Registry description payload: {self.agent._format_bytes(len(tools_description))}[/dim]\n",
                    sep="",
                )

            case "/trace":
                trace = self.agent.traces["solution"]
                for i, step in enumerate(trace):
                    self.console.print(f"[bold yellow]Trace {i+1}:[/bold yellow]")
                    print(f"{step}\n")

            case "/history":
                for i, chat in enumerate(self.agent.history[1:]):
                    self.console.print(f"[bold yellow]Chat {i+1}:[/bold yellow]")
                    print(f"{chat}\n")
                self.console.print(
                    f"[dim]Session history payload: {self.agent._format_bytes(len(str(self.agent.history)))}[/dim]\n",
                )

            # case "/vhistory":
            #     for i, chat in enumerate(self.agent.verificator_history[1:]):
            #         self.console.print(f"[bold yellow]Chat {i+1}:[/bold yellow]")
            #         print(f"{chat}\n")

            case "/infocontext":
                bytes_ = sum(len(str(item)) for item in self.agent.history)
                self.console.print(
                    f"[dim][bold]History:[/bold] {len(self.agent.history)} messages[/dim]\n",
                    f"[dim][bold]Context size:[/bold] ~{self.agent._format_bytes(bytes_)}[/dim]\n",
                    sep="",
                )

            case "/savetrace":
                try:
                    filename = self.agent.dump_trace()
                    self.console.print(f"[dim]Trace saved in {filename}[/dim]\n")
                except Exception as e:
                    self.console.print(
                        f"[bold red]Error saving trace:[/bold red] {e}\n"
                    )

            case "/savecontext":
                try:
                    self.agent.dump_history()
                    self.console.print("[dim]Context state persisted to disk.[/dim]\n")
                except Exception as e:
                    self.console.print(
                        f"[bold red]Context persistence error:[/bold red] {e}\n"
                    )

            case "/loadcontext":
                try:
                    self.agent.restore_history()
                    self.console.print(
                        "[dim]Context recovered. Session state synchronized.[/dim]\n"
                    )
                except Exception as e:
                    self.console.print(
                        f"[bold red]Context restoration error:[/bold red] {e}\n"
                    )

            case "/infoknowledge":
                knowledge_info = self.agent.knowledge.get_db_info()

                self.console.print(
                    f"[dim][bold]Number of documents:[/bold] {knowledge_info['total_documents']}[/dim]\n",
                    f"[dim][bold]Database size:[/bold] ~{self.agent._format_bytes(knowledge_info['disk_size_bytes'])}[/dim]\n",
                    sep="",
                )

            case "/rollback":
                if (
                    not self.agent.state_manager
                    or not self.agent.state_manager.get_states()
                ):
                    self.console.print(
                        "[dim]No state manager available to perform rollback.[/dim]\n"
                    )
                    return

                if not args:
                    commit_hash = self.agent.restore_previous_state()
                    self.console.print(
                        f"[dim]State rolled back to previous checkpoint [{commit_hash}].[/dim]\n"
                    )
                else:
                    restored = self.agent.state_manager.restore_state(args[0])
                    if restored:
                        self.console.print(
                            f"[dim]State successfully restored to {args[0]}.[/dim]\n"
                        )
                    else:
                        self.console.print(
                            f"[dim]Failed to restore state: commit '{args[0]}' not found or invalid.[/dim]\n"
                        )

        self.console.print(
            Markdown("----"),
            end="",
        )

    def is_command(self, command):
        command, args = command.split(" ", 1)
        return command in COMMANDS

    def get_command(self, command):
        command, *args = command.split(" ")
        return command, args

    def repl(self):
        logging.basicConfig(level=logging.CRITICAL)
        self.show_welcome()
        self.pretty_print("----")

        session = PromptSession(
            erase_when_done=True,
            history=self.prompt_history,
            completer=self.completer,
            mouse_support=False,
        )

        def as_table(prompt, message="", color="cyan"):
            table = Table.grid(expand=True)
            table.add_column(width=len(prompt) + 1)
            table.add_column()

            table.add_row(
                Text(prompt, style=f"bold {color}"),
                Markdown(message),
            )
            return table

        input_prompt = "&gt;&gt;&gt; "  # >>>
        input_prompt_history = "USER |"
        output_prompt_history = "DEER |"

        while True:
            try:
                msg = session.prompt(
                    HTML(f"<ansicyan><b>{input_prompt}</b></ansicyan>")
                )
                # msg = input(">>> ")
                self.save_prompt_history()

                if self.agent.load_history:
                    self.agent.dump_history()

            except KeyboardInterrupt:
                continue
            except EOFError:
                break

            if not msg.strip():
                continue

            if self.get_command(msg)[0] in COMMANDS:
                command, args = self.get_command(msg)
                self.console.print(
                    as_table(f"[{command}]", color="cyan"),
                    Text("\n"),
                    end="",
                )
                self.run_command(command, args)

            elif msg.startswith("!"):
                cmd_to_run = msg[1:].strip()

                self.console.print(
                    as_table(f"[{cmd_to_run}]", color="cyan"),
                    Text("\n"),
                    end="",
                )

                try:
                    # Execute the command
                    result = subprocess.run(
                        cmd_to_run,
                        shell=True,
                        capture_output=True,
                        text=True,
                        check=True,
                    )
                    self.console.print(
                        Text(result.stdout),
                        Markdown("----"),
                        sep="",
                    )

                except subprocess.CalledProcessError as e:
                    self.console.print(
                        f"[dim]Error executing command: {e.stderr}[/dim]",
                        Markdown("----"),
                        sep="",
                    )
                except Exception as e:
                    self.console.print(
                        f"[dim]An unexpected error occurred: {e}[/dim]",
                        Markdown("----"),
                        sep="",
                    )

            elif msg.startswith("/"):
                self.pretty_print(
                    f"Command `{msg}` not recognized. Did you mean one of these: {list(COMMANDS)}"
                )

            elif msg.startswith("?"):
                status = self.console.status(
                    "[dim]processing request[/]\n",
                    spinner="point",
                    spinner_style="dim",
                )
                status.start()

                try:
                    self.console.print(
                        as_table(input_prompt_history, msg),
                        Text("\n"),
                        end="",
                    )
                    status.stop()

                    # Call the LLM model
                    full_response = ""
                    with Live(
                        "",
                        console=self.console,
                        refresh_per_second=60,
                        vertical_overflow="visible",
                    ) as live:
                        for token in self.agent.run_stream(msg):
                            full_response += token
                            live.update(
                                as_table(
                                    output_prompt_history,
                                    full_response.strip(),
                                )
                            )

                    self.console.print(
                        Text("\n"),
                        Markdown("----"),
                        end="",
                    )

                except KeyboardInterrupt:
                    self.console.print(
                        "[dim]Command aborted by user[/dim]\n",
                        Markdown("----"),
                        sep="",
                    )
                    continue

                except RuntimeError as e:
                    self.console.print(
                        f"[dim]{e}[/dim]\n",
                        Markdown("----"),
                        sep="",
                    )
                    continue

                except EOFError:
                    break

            else:

                with self.console.status(
                    "[dim]processing request[/]",
                    spinner="point",
                    spinner_style="dim",
                ):
                    try:
                        self.console.print(
                            as_table(input_prompt_history, msg),
                            Text("\n"),
                            end="",
                        )

                        # Call the LLM model
                        response = self.agent.run(msg)

                        self.console.print(
                            as_table(output_prompt_history, response),
                            Text("\n"),
                            Markdown("----"),
                            end="",
                        )

                    except KeyboardInterrupt:
                        self.console.print(
                            "[dim]Command aborted by user[/dim]\n",
                            Markdown("----"),
                            sep="",
                        )
                        continue

                    except RuntimeError as e:
                        self.console.print(
                            f"[dim]{e}[/dim]\n",
                            Markdown("----"),
                            sep="",
                        )
                        continue

                    except EOFError:
                        break
