import os
from pathlib import Path

__version__ = "0.1.7"


def load_env_file(env_path: Path) -> None:
    """Reads a .env file and loads its variables into os.environ natively."""
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                # Strip whitespace and ignore empty lines or comments
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                # Split by the first '=' found
                if "=" in line:
                    key, value = line.split("=", 1)
                    # Strip quotes if the value is wrapped in them
                    key = key.strip()
                    value = value.strip().strip("'\"")

                    # Set the environment variable
                    os.environ[key] = value
    except IOError as e:
        # Log or handle the error if the file exists but can't be read
        pass


# Your configuration logic remains clean and dependency-free
local_env = Path(".env")
user_env = Path.home() / ".deer.env"

if local_env.exists():
    load_env_file(local_env)
elif user_env.exists():
    load_env_file(user_env)
