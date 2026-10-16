#!/bin/bash

# --- 1. ENVIRONMENT LOADING ---
# Load variables from the .env file if it exists
if [ -f .env ]; then
    set -a            # Automatically export all variables
    source .env       # Read the file
    set +a            # Disable automatic exporting
else
    echo "Error: .env file not found"
    exit 1
fi

# --- 2. PATH CONFIGURATION ---
# Dynamically determine the project root directory based on the script's location
# This prevents errors when running the script from a different folder
PROJECT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
VENV_PATH="$PROJECT_DIR/.venv/bin/activate"

# Set the default agent (can be changed or passed as an argument)
AGENT="python-syntax-specialist"
#AGENT="operating-system"

# --- 3. COMMAND BUILDER FUNCTION ---
# This function encapsulates the command logic to make it modular and reusable
build_agent_command() {
    local agent_name=$1

    # FIX: We use single quotes (') instead of escaped double quotes (\")
    # This prevents AppleScript (osascript) from getting confused.
    local cmd="if [ -f '$ENV_PATH' ]; then set -a; source '$ENV_PATH'; set +a; fi && \
               source '$VENV_PATH' && \
               export PYTHONPATH='\$PYTHONPATH:$PROJECT_DIR' && \
               python '$PROJECT_DIR/deer/builtins_agents/$agent_name/agent.py' \
               --path '$WORKING_DIR' \
               --backend '$DEER_BACKEND' \
               --model '$DEER_BACKEND_MODEL'"
    echo "$cmd"
}

# --- 4. EXECUTION ---
# Generate the final command string using the function
CMD=$(build_agent_command "$AGENT")

# Use osascript to open a new macOS Terminal window and execute the command.
# We wrap the command in escaped quotes to ensure it is passed as a single string.
osascript -e "tell application \"Terminal\"" \
            -e "activate" \
            -e "do script \"cd '$PROJECT_DIR/sandbox' && $CMD\"" \
            -e "end tell"