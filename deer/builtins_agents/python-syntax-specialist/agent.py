from pathlib import Path

from deer import DeterministicAgent
from deer.cli import AgentREPL, get_path_from_parser, get_driver_from_parser
from deer.drivers import OllamaDriver
from deer.memory import VectorMemory

from providers import PEPProvider

# Infrastructure
driver = get_driver_from_parser()
working_dir = get_path_from_parser() or Path.cwd()
knowledge = VectorMemory(path=working_dir / "pss_knowledge")
registry = {PEPProvider}

identity = (Path(__file__).parent / "identity.md").read_text(encoding="utf-8")

agent = DeterministicAgent(
    description="Python Syntax Specialist",
    identity=identity,
    driver=driver,
    knowledge=knowledge,
    tool_registry=registry,
    working_dir=working_dir,
    max_attempts=3,
    enable_verification=False,
    vector_contex_limit=5,
)

print(driver.model_name)


knowledge_path = Path(__file__).parent / "knowledge"
agent.knowledge.read_directory(doc_id_prefix="pss", path=knowledge_path)

documents = ", ".join([f.name for f in knowledge_path.iterdir() if f.is_file()])
agent.knowledge.add_document(
    doc_id="all_knowledge",
    doc=(
        f"This is the complete list of PEP documents currently stored in local context: {documents}. "
        "IMPORTANT: If a requested PEP is not present in this list, it does NOT mean it does not exist. "
        "You MUST fetch it from the external repository using the `pep_inquiry` tool before answering."
    ),
    metadata="",
)


def main():
    repl = AgentREPL(agent)
    repl.repl()


if __name__ == "__main__":
    main()
