import logging

from deer.core.agent import DeterministicAgent
from deer.drivers import GeminiDriver, OllamaDriver

from tools import registry
from dotenv import load_dotenv

load_dotenv()
logging.getLogger("DEER").setLevel(logging.DEBUG)

# driver = GeminiDriver(model_name="gemini-3.1-flash-lite")
# driver = GeminiDriver(model_name="gemini-1.5-flash-lite")
# driver = OllamaDriver(model_name="qwen2.5-coder:7b")
driver = OllamaDriver(model_name="gemma4:31b-cloud")
agent = DeterministicAgent(
    identity="You are a senior Python packaging and environment management specialist with deep expertise in"
    "pyproject.toml, dependency management, reproducible environments, build systems, virtual environments, "
    "and modern Python tooling ecosystems including pip, setuptools, pytest",
    driver=driver,
    registry=registry,
    format_response="markdown",
)
# agent.repl()


if __name__ == "__main__":
    chain_messages = [
        "Quiero que generes un archivo llamado 'example.py' con ejemplo de un script en python que imprima un 'Hola mundo'.",
        "Quiero que edites el archivo 'example.py' que agreges un función llamada 'main'.",
        # "Write 'Secret Code 789' to a file named 'secret.txt'"
    ]

    for message in chain_messages:
        print(f">>> {message}\n")
        response = agent.send(message)
        print(f"    {response.text()}\n\n")
