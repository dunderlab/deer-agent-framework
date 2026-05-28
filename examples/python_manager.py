from deer.builtins.python_manager.agent import agent

from prompts import (
    SIMPLE_FILE_CREATION_PROMPT,
    PYTHON_PROJECT_PROMPT,
    SEQUENTIAL_FILE_EDITION_PROMPT,
)

jail_path = "/Users/yeison/Development/deer-agent-framework/sandbox/root"
agent.set_jail(jail_path)


# agent.iterate_debug(
#     [*PYTHON_PROJECT_PROMPT],
#     repetitions=50,
#     path="traces/python_project4",
# )

chain = [
    " que carpetas existen ahora mismo?",
    # "lista los archivos locales",
    # "eliminalos",
]

for message in chain:
    print(f">>> {message}")
    response = agent.send(message)
    print(f"    {response.result}")
    print()
