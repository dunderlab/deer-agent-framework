import argparse
import sys
import os

from .base_driver import LLMDriver
from .gemini_driver import GeminiDriver
from .ollama_driver import OllamaDriver

from deer.utils.console import error

backends = {
    "gemini",
    "openai",
    "ollama",
}

drivers_parser = argparse.ArgumentParser(description="DEER Agent Framework CLI")

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


def get_driver_from_parser():

    args = drivers_parser.parse_args()

    if args.backend not in backends:
        error(
            f"Unsupported backend '{args.backend}'. "
            f"Supported backends are: {', '.join(backends)}."
        )
        sys.exit(1)

    if not args.model:
        error("A model identifier must be provided.")
        sys.exit(1)

    match args.backend:

        case "gemini":
            return GeminiDriver(model_name=args.model)

        case "ollama":
            return OllamaDriver(model_name=args.model)

        case "openai":
            pass
            # return OpenAIDriver(model_name=args.model)
