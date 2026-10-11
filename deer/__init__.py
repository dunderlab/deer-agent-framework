from pathlib import Path
import sys

from dotenv import load_dotenv

from deer.core import DeterministicAgent

version_info = "0.2"

local_env = Path(sys.path[0]) / ".env"
user_env = Path.home() / ".deer.env"

if local_env.exists():
    load_dotenv(local_env)
elif user_env.exists():
    load_dotenv(user_env)
