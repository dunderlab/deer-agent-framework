import shutil
from pathlib import Path

from deer.builtins.python_manager.agent import agent
from deer.core.agent import logger, logging

logger.setLevel(logging.DEBUG)

from prompts import (
    SIMPLE_FILE_CREATION_PROMPT,
    PYTHON_PROJECT_PROMPT,
    SEQUENTIAL_FILE_EDITION_PROMPT,
)

jail_path = Path("/Users/yeison/Development/DEER/sandbox/root")
agent.set_jail(jail_path)
print(agent.tool_registry.describe())


def purge_jail():
    shutil.rmtree(jail_path)
    jail_path.mkdir(parents=True, exist_ok=True)


# agent.send(
#     message="Al archivo pyproject.toml agrega la dependencia de matplotlib",
#     print_chat=True,
# )

agent.repl()

# purge_jail()
# agent.iterate_debug(
#     chain_messages=PYTHON_PROJECT_PROMPT,
#     repetitions=100,
#     path="/Users/yeison/Development/DEER/traces/python_project17",
#     callback=purge_jail,
# )
