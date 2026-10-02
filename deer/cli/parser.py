import argparse
import os
from pathlib import Path

from deer.utils.console import ConsoleColor

backends = {
    "gemini",
    "openai",
    "ollama",
    "azure",
}


class NoExitArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        if getattr(self, "silent", False):
            raise ValueError(message)
        else:
            return super().error(message)


drivers_parser = NoExitArgumentParser(description="DEER Agent Framework CLI")
# drivers_parser = argparse.ArgumentParser(description="DEER Agent Framework CLI")

drivers_parser.add_argument(
    "agent",
    nargs="?",
    help="Name of the agent to execute",
)

drivers_parser.add_argument(
    "--backend",
    default=os.environ.get("DEER_BACKEND"),
    required=os.environ.get("DEER_BACKEND") is None,
    choices=backends,
    help="Inference backend to use",
)

drivers_parser.add_argument(
    "--model",
    default=os.environ.get("DEER_BACKEND_MODEL"),
    required=os.environ.get("DEER_BACKEND_MODEL") is None,
    help="Model identifier for the selected backend",
)

path_parser = NoExitArgumentParser(description="DEER Agent Framework CLI")

path_parser.add_argument(
    "--path",
    default=os.environ.get("DEER_PATH"),
    required=False,
    help="The root directory of the agent where it will perform its work and operations",
)


def get_driver_from_parser():

    from deer.drivers import GeminiDriver, OllamaDriver, OpenAIDriver, AzureOpenAIDriver

    try:
        drivers_parser.silent = True
        args = drivers_parser.parse_args()
        drivers_parser.silent = False
    except:
        drivers_parser.silent = False
        return False

    if args.backend not in backends:
        ConsoleColor.on_error(
            f"Unsupported backend '{args.backend}'. "
            f"Supported backends are: {', '.join(backends)}."
        )
        return False

    if not args.model:
        ConsoleColor.on_error("A model identifier must be provided.")
        return False

    match args.backend:

        case "gemini":
            return GeminiDriver(model_name=args.model)

        case "ollama":
            return OllamaDriver(model_name=args.model)

        case "openai":
            return OpenAIDriver(model_name=args.model)

        case "azure":
            return AzureOpenAIDriver(model_name=args.model)


def get_path_from_parser():

    try:
        path_parser.silent = True
        args = path_parser.parse_args()
        path_parser.silent = False
    except:
        path_parser.silent = False
        return False

    if not args.path:
        return False
    else:
        return Path(args.path).resolve()
