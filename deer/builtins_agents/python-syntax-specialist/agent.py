from pathlib import Path

from tomlkit import document

from deer import DeterministicAgent
from deer.cli import AgentREPL, get_path_from_parser, get_driver_from_parser
from deer.drivers import OllamaDriver
from deer.memory import VectorMemory

# Infrastructure
driver = get_driver_from_parser() or OllamaDriver(model_name="gemma4:31b-cloud")
working_dir = get_path_from_parser() or Path.cwd()
knowledge = VectorMemory(path=working_dir / "pss_knowledge")

identity = (Path(__file__).parent / "identity.md").read_text(encoding="utf-8")

agent = DeterministicAgent(
    description="Python Syntax Specialist",
    identity=identity,
    driver=driver,
    knowledge=knowledge,
    working_dir=working_dir,
    max_attempts=3,
    enable_verification=False,
    vector_contex_limit=5,
)


knowledge_path = Path(__file__).parent / "knowledge"
agent.knowledge.read_directory(doc_id_prefix="pss", path=knowledge_path)

documents = ", ".join([f.name for f in knowledge_path.iterdir() if f.is_file()])
agent.knowledge.add_document(
    doc_id="all_knowledge",
    doc=f"This is the list of all documents and PEPs that you can access: {documents}",
    metadata="",
)


def main():
    repl = AgentREPL(agent)
    repl.repl()


if __name__ == "__main__":
    main()
