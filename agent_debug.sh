#!/bin/bash

# 1. Define the absolute project path to avoid errors in the new window
PROJECT_DIR=$(pwd)
VENV_PATH="$PROJECT_DIR/.venv/bin/activate"
WORKING_DIR="$PROJECT_DIR/sandbox"
DEER_BACKEND="ollama"
DEER_BACKEND_MODEL="gemma4:31b-cloud"
#DEER_BACKEND_MODEL="nemotron-3-ultra:cloud"
#AGENT="operating_system.py"
#AGENT="python_architect.py"
#AGENT="deer_introspection.py"
AGENT="python-syntax-specialist"


# 2. Build the full command to be executed in the new window
# Combine environment activation, PYTHONPATH, and script execution
CMD="source $VENV_PATH && export PYTHONPATH=\$PYTHONPATH:$PROJECT_DIR && python $PROJECT_DIR/deer/builtins_agents/$AGENT/agent.py --path $WORKING_DIR --backend $DEER_BACKEND --model $DEER_BACKEND_MODEL"

# 3. Execute osascript correctly to open the window and launch the command
osascript -e "tell application \"Terminal\" to do script \"$CMD\""