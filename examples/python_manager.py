from deer.builtins.python_manager.agent import agent

from prompts import (
    SIMPLE_FILE_CREATION_PROMPT,
    PYTHON_PROJECT_PROMPT,
    SEQUENTIAL_FILE_EDITION_PROMPT,
)

jail_path = "/Users/yeison/Development/deer-agent-framework/sandbox/root"
agent.set_jail(jail_path)


agent.iterate_debug(
    [*PYTHON_PROJECT_PROMPT],
    repetitions=50,
    path="traces/python_project4",
)

# response = agent.send("Hola")
# print(response.result)
