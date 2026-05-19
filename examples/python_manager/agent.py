import logging

logging.getLogger("DEER").setLevel(logging.DEBUG)


from deer.core.agent import DeterministicAgent
from deer.drivers.gemini_driver import GeminiDriver

from tools import registry
from dotenv import load_dotenv

load_dotenv()

driver = GeminiDriver(model_name="gemini-3.1-flash-lite")
agent = DeterministicAgent(
    identity="You are a senior Python packaging and environment management specialist with deep expertise in"
    "pyproject.toml, dependency management, reproducible environments, build systems, virtual environments, "
    "and modern Python tooling ecosystems including pip, setuptools, pytest",
    driver=driver,
    registry=registry,
    format_response="markdown",
)
# agent.repl()
response = agent.send("""
    Quiero que generes un archivo llamado 'example.py' con ejemplo de un script en python que imprima un "
    "'Hola mundo'
    """)
print(response)


response = agent.send("""
    Quiero que edites el archivo 'example.py' que agreges un función llamada 'main'.
    """)
print(response)
