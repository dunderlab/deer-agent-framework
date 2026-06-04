from deer.builtins.python_manager.agent import agent

from prompts import (
    SIMPLE_FILE_CREATION_PROMPT,
    PYTHON_PROJECT_PROMPT,
    SEQUENTIAL_FILE_EDITION_PROMPT,
)

jail_path = "/Users/yeison/Development/DEER/sandbox/root"
agent.set_jail(jail_path)

print(agent.tool_registry.describe())


# agent.repl()
