# DEER: Deterministic Executable Engine for Runtime Agents

### **Stop building "Vibe-based" Agents. Start Engineering Deterministic Systems.**

**DEER** is a professional-grade framework designed to transform LLMs from probabilistic text-generators into
**Deterministic Autonomous Engineers**. While other frameworks rely on massive, fragile system prompts and hope for the
best, DEER subordinates the LLM to a rigid, code-defined execution pipeline where every action is typed, validated, and
physically verified.

![License](https://img.shields.io/badge/license-BSD--2--Clause-blue.svg)
![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)
![GitHub top language](https://img.shields.io/github/languages/top/dunderlab/deer-agent-framework)
![PyPI - License](https://img.shields.io/pypi/l/deer-agent-framework)
![PyPI](https://img.shields.io/pypi/v/deer-agent-framework)
![PyPI - Status](https://img.shields.io/pypi/status/deer-agent-framework)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/deer-agent-framework)
![GitHub last commit](https://img.shields.io/github/last-commit/dunderlab/deer-agent-framework)
![CodeFactor Grade](https://img.shields.io/codefactor/grade/github/dunderlab/deer-agent-framework)
![Upload Python Package](https://github.com/dunderlab/deer-agent-framework/actions/workflows/python-publish.yml/badge.svg)

---

## Why DEER?

* **Execution over Prompts:** Behavior is defined by a rigid pipeline of validated tool calls, not by massive, fragile
  text prompts.
* **Typed Contracts:** Every tool uses Pydantic models for input and output, ensuring zero hallucinated arguments.
* **Multi-Layered Security:** Combines a filesystem jail with an AST-whitelist sandbox to block dangerous code
  injection.
* **Evidence-Based Verification:** The agent doesn't just "claim" success; it executes a separate verification plan to
  physically prove the goal was achieved.

DEER decouples an agent's **Identity** from its **Capabilities**. You do not change a prompt to give an agent new
powers; you extend its `ToolRegistry` or enrich its `VectorMemory`. This transforms the agent's evolution from a
probabilistic exercise in prompt engineering into a programmatic and traceable process.

* **Execution over Prompts:** Behavior is governed by a rigid pipeline of validated tool calls, not by massive, fragile
  system prompts. The agent's logic is subordinate to the code.
* **Surgical Precision:** Unlike agents that overwrite files or use fragile regex, DEER employs Concrete Syntax Tree
  (CST) transformations. This allows the agent to perform semantic surgery—updating functions and refactoring
  classes—while preserving the original code's integrity.
* **Strict Typed Contracts:** Every tool is governed by Pydantic models for both input and output. This eliminates
  hallucinated arguments and ensures that data flowing between tools is always valid.
* **Principle of Least Privilege:** Security is implemented at the tool level. Through specialized runners, an agent's
  access is scoped to its role (e.g., a Developer cannot execute system-level chmod commands), combining a filesystem
  jail with a strict binary allow-list.
* **Evidence-Based Verification:** DEER eliminates "hallucinated success." The agent does not simply claim a goal is
  achieved; it must execute a separate, read-only verification plan to physically prove the result.

> **No Arbitrary Execution**
> DEER strictly forbids the execution of raw, LLM-generated code. An agent's capabilities are defined programmatically
> through its `ToolRegistry`. If a capability is not explicitly defined as a typed Tool, it does not exist for the
> agent.
> This ensures that the model can only interact with the world through secure, validated, and audited interfaces.

---

## The DEER Workflow: Architecting Deterministic Agents

DEER decouples an agent's reasoning from its capabilities. You do not build an agent by writing a massive prompt; you
architect it by assembling three core pillars: **Identity**, **Capabilities**, and **Knowledge**.

### 1. Assembling the Agent's Core

The agent is initialized by combining a driver (reasoning engine), a memory system (long-term knowledge), and a tool
registry (operational capabilities). This ensures the agent's behavior is a result of its configured infrastructure, not
probabilistic luck.

```python
from pathlib import Path
from deer.core.agent import DeterministicAgent
from deer.memory import VectorMemory
from deer.drivers import OllamaDriver
from deer.tools import ToolRegistry, Preset

# Infrastructure
driver = OllamaDriver(model_name="llama3")
memory = VectorMemory(path="./agent_memory")
registry = ToolRegistry(Preset.CODE_REPAIR | Preset.CODE_EDITOR | Preset.DATA_ANALYST)

agent = DeterministicAgent(
    description="Python Architecture Specialist",
    identity=(
        "You are a Principal Python Architect. You possess authoritative expertise "
        "in advanced module resolution and dependency management."
    ),
    driver=driver,
    memory=memory,
    tool_registry=registry,
    jail_path=Path.cwd() / "sandbox",
    max_attempts=5,
)

if __name__ == "__main__":
    # Run a deterministic goal
    result = agent.run("Create a project structure for a data processor")
    print(result)
```

### 2. Extending Capabilities via Tool Registries

Capabilities are modular. You can extend an agent's reach by registering specialized tool providers. This allows you to
scale an agent's power from basic file operations to complex system management without altering the core agent logic.

```python
from deer.tools.registry import ToolRegistry
from deer.tools.providers import FileManager, GitManager, CodeSearcher

tool_registry = ToolRegistry({FileManager | GitManager | CodeSearcher})

```

### 3. Defining Custom Deterministic Logic

The framework is an open canvas. You can define entirely new capabilities by inheriting from `ToolProvider`. By using
Pydantic-style return types and strict type hints, you ensure that the agent's interactions with the external world are
typed, validated, and predictable.

```python
from deer.tools import ToolProvider, tool
from deer.tools.schemas import Return


class MyCustomProvider(ToolProvider):
    @tool(modifies_state=True)
    def deploy_module(self, name: str, version: str) -> Return(status=str, job_id=int):
        """Deploys a specific python module to the internal repo."""
        # Implement the deterministic execution logic here
        return {"status": "success", "job_id": 12345}

```

---

## Built-in Deterministic Agents

The framework includes pre-configured **Deterministic Agents** in the `deer/builtins/` directory. These serve as both
ready-to-use tools and reference implementations for building your own specialized architects and managers.

---

## Technical Differentiation

| Feature               | Traditional Frameworks (LangChain, etc.) | **DEER Deterministic Agents**                    |
|:----------------------|:-----------------------------------------|:-------------------------------------------------|
| **Execution Flow**    | Probabilistic (LLM decides next step)    | **Deterministic** (Plan-Validate-Execute-Verify) |
| **Tool Arguments**    | Often Hallucinated                       | **Strictly Typed** (Pydantic Models)             |
| **Code Modification** | Text-based / Full-file Overwrites        | **Surgical CST Transformation** (Semantic Edits) |
| **Impact Analysis**   | Grep-based / None                        | **Semantic Dependency Mapping**                  |
| **Security**          | None / Manual                            | **Built-in Jail + AST-Whitelist Sandbox**        |
| **Debugging**         | Black box / Tricky logs                  | **Step-by-Step Execution Trace Replay**          |
| **Output**            | Raw Text                                 | **Validated & Humanized Synthesis**              |
| **Memory**            | Static Window / Basic RAG                | **Adaptive** (Popularity-Aware & Auto-Pruning)   |

---

## The "Assembly Line" Lifecycle

A **Deterministic Agent** in DEER does not "guess" its way to a solution. It processes every request through a linear,
audited production line:

1. **Contextual Grounding:** The agent queries the popularity-aware vector memory to retrieve the most relevant domain
   knowledge and architectural constraints.
1. **Deterministic Planning:** A structured JSON pipeline is generated. This is not a suggestion, but a strict sequence
   of tool
   calls with explicitly defined expected return types.
1. **Static Audit:** The `PlanValidator` audits the pipeline for type-safety, reference integrity, and security
   compliance before
   a single line of code is executed.
1. **Surgical Execution:** Tools are executed within a secure, isolated jail. Whether performing a CST-based code
   transformation or a system-level mutation, every action is routed through a validated `ToolProvider`.
1. **Physical Evidence Verification:** To eliminate "hallucinated success," a separate, read-only verification plan is
   executed. The agent must physically prove the goal was achieved (e.g., by verifying the file exists or the process is
   running).
1. **Professional Synthesis:** The complete `ExecutionTrace` is analyzed to provide a final, human-readable conclusion,
   backed by
   the evidence gathered during the verification phase.

---

## Installation

From PyPI:

```bash
pip install deer-agent-framework
```

From GitHub (development version):

```bash
pip install git+https://github.com/dunderlab/deer-agent-framework.git
```

*Requires Python 3.12+ and a valid LLM API Key (Gemini, Ollama, etc.).*

---

## License

Licensed under the **BSD 2-Clause License**. See [LICENSE](LICENSE) for details.

---
**Built for developers who trust code, not prompts.**