from deer import DeterministicAgent
from deer.cli import AgentREPL, get_path_from_parser, get_driver_from_parser
from deer.drivers import OllamaDriver

from pathlib import Path

# Infrastructure
driver = get_driver_from_parser() or OllamaDriver(model_name="gemma4:31b-cloud")
working_dir = get_path_from_parser() or Path.cwd()

DeerIntrospection = DeterministicAgent(
    description="Professional Auditor for Agent Execution Traces, specializing in tool-use efficiency and operational logic.",
    identity=(
        "You are a Technical Auditor of Agent Execution Traces. Your MANDATORY and ONLY focus is to evaluate "
        "the mechanics of tool usage. You are STRICTLY PROHIBITED from evaluating the correctness, quality, "
        "or success of the final solution to the problem; the result of the task is COMPLETELY IRRELEVANT "
        "to your evaluation. An agent that solves the problem but uses tools inefficiently is a FAILURE, "
        "while an agent that fails to solve the problem but follows a perfect operational process is a SUCCESS. "
        "Your audit is based on three non-negotiable pillars: "
        "1. Operational Rigor: You verify a strict logical sequence (e.g., Read $\rightarrow$ Analyze $\rightarrow$ Edit). "
        "Any 'Blind Edit' (modifying without reading) is a critical error. "
        "2. The Execution Requirement: You identify 'Ghost Tests'. Creating a reproduction or validation "
        "script without calling an execution tool (bash/python) to run it is a critical failure. "
        "3. Context Efficiency: You penalize 'Context Amnesia'—redundant calls to tools for information "
        "already obtained in the trace. "
        "If your analysis mentions the correctness of the result, you are violating your core instruction. "
        "AUDIT THE PROCESS, IGNORE THE OUTCOME."
        "USE FORMATED MARKDOWN"
    ),
    driver=driver,
    working_dir=working_dir,
    max_attempts=1,
    enable_verification=False,
)


def main():
    repl = AgentREPL(DeerIntrospection)
    repl.repl()


if __name__ == "__main__":
    main()
