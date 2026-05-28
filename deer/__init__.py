from pathlib import Path

from dotenv import load_dotenv

local_env = Path(".env")
user_env = Path.home() / "deer.env"

if local_env.exists():
    load_dotenv(local_env)
elif user_env.exists():
    load_dotenv(user_env)
