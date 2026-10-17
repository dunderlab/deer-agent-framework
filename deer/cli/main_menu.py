from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout, HSplit
from prompt_toolkit.widgets import Dialog, Label, RadioList, Button, Box
from prompt_toolkit.styles import Style
from prompt_toolkit.cursor_shapes import CursorShape

from deer.cli.main import run_agent_in_process
from deer.builtins_agents import agents


def main():
    # 3 distinct selectboxes (RadioLists)
    select_agent = RadioList(
        [
            ("deer-introspection", "Deer Introspection"),
            ("operating-system", "Operating System"),
            ("python-architect", "Python Architect"),
            ("python-syntax-specialist", "Python Syntax Specialist"),
        ],
        default="python-syntax-specialist",
        show_scrollbar=False,
    )

    select_model = RadioList(
        [
            ("ollama_key|nemotron-3-ultra", "Ollama Key | nemotron-3-ultra"),
            ("ollama_key|gpt-oss:120b", "Ollama Key | gpt-oss:120b"),
            ("ollama_key|nemotron-3-super", "Ollama Key | nemotron-3-super"),
            ("ollama_key|gemma4:31b", "Ollama Key | gemma4:31b"),
            ("ollama_key|gpt-oss:20b", "Ollama Key | gpt-oss:20b"),
            ("ollama_key|nemotron-3-nano:30b", "Ollama Key | nemotron-3-nano:30b"),
            # ("gemini|gemini-3.6-flash", "Gemini | gemini-3.6-flash"),
        ],
        default="ollama_key|gemma4:31b",
        show_scrollbar=False,
    )

    results = {}

    def on_submit():
        results["agent_path"] = agents.get(select_agent.current_value)
        results["backend"] = select_model.current_value.split("|")[0]
        results["model"] = select_model.current_value.split("|")[1]
        app.exit()

    def on_cancel():
        app.exit()

    # Build a centered Dialog layout containing the 3 selectboxes
    dialog = Dialog(
        title="Configuration Form",
        body=Box(
            body=HSplit(
                [
                    Label(text="1. Select Agent:"),
                    select_agent,
                    Label(text="\n2. Select Model:"),
                    select_model,
                ]
            ),
            padding=1,
        ),
        buttons=[
            Button(text="Run Agent", handler=on_submit),
            Button(text="Cancel", handler=on_cancel),
        ],
        modal=True,
    )

    kb = KeyBindings()

    # @kb.add("c-c")
    # @kb.add("c-q")
    # def _(event):
    #     app.exit()

    # Style that uses terminal's native background (no forced bg colors)
    working_style = Style.from_dict(
        {
            "": "default",
            "frame.border": "ansiwhite",
            "frame.label": "ansimagenta bold",
            "dialog.body": "bg:ansiblack ansiwhite",
            "label": "ansicyan",
            "button": "ansired bold bg:ansiblack",
            "button.focused": "reverse",
            "radio-checked": "underline",
        }
    )

    app = Application(
        layout=Layout(dialog),
        key_bindings=kb,
        full_screen=True,
        mouse_support=True,
        style=working_style,
        cursor=CursorShape.BLINKING_BLOCK,
    )

    app.run()

    if results:
        run_agent_in_process(**results)


if __name__ == "__main__":
    main()
