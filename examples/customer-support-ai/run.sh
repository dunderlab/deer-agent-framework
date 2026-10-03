#!/bin/bash

PROJECT_DIR=$(pwd)
VENV_PATH="$PROJECT_DIR/../../.venv/bin/activate"
WORKING_DIR="$(pwd)/sandbox"
PROJECT_ROOT="$PROJECT_DIR/../../"
AGENT="agent.py"

CMD="source $VENV_PATH && export PYTHONPATH=\$PYTHONPATH:$PROJECT_ROOT && python $PROJECT_DIR/$AGENT --path $WORKING_DIR"
osascript -e "tell application \"Terminal\" to do script \"$CMD\""
