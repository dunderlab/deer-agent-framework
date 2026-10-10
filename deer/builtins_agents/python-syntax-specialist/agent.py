from pathlib import Path
import os

from deer import DeterministicAgent
from deer.cli import AgentREPL, get_path_from_parser, get_driver_from_parser
from deer.drivers import OllamaDriver
from deer.memory import VectorMemory

# Infrastructure
driver = get_driver_from_parser() or OllamaDriver(model_name="gemma4:31b-cloud")
working_dir = get_path_from_parser() or Path.cwd()
memory = VectorMemory(path=working_dir / "pss_memory")

identity = (Path(__file__).parent / "identity.md").read_text(encoding="utf-8")

pss = DeterministicAgent(
    description="Python Syntax Specialist",
    identity=identity,
    driver=driver,
    vector_memory=memory,
    working_dir=working_dir,
    max_attempts=3,
    enable_verification=False,
)

pss.vector_memory.read_directory(
    doc_id_prefix="pss", path=Path(__file__).parent / "memory"
)


def main():
    repl = AgentREPL(pss)
    repl.repl()


if __name__ == "__main__":
    main()
