#!/bin/bash

# 1. Define the absolute project path to avoid errors in the new window
PROJECT_DIR=$(pwd)
VENV_PATH="$PROJECT_DIR/.venv/bin/activate"
WORKING_DIR="$PROJECT_DIR/sandbox"
AGENT="operating_system.py"
#AGENT="python_architect.py"

# 2. Build the full command to be executed in the new window
# Combine environment activation, PYTHONPATH, and script execution
CMD="source $VENV_PATH && export PYTHONPATH=\$PYTHONPATH:$PROJECT_DIR && python $PROJECT_DIR/deer/builtins_agents/$AGENT --path $WORKING_DIR"

# 3. Execute osascript correctly to open the window and launch the command
osascript -e "tell application \"Terminal\" to do script \"$CMD\""