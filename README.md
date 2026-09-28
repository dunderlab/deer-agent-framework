# DEER: Deterministic Executable Engine for Runtime Agents

### **Stop building "Vibe-based" Agents. Start Engineering Deterministic Agents.**

**DEER** is a professional-grade framework designed for building **Deterministic Agents** in production environments.
While other frameworks rely on massive system prompts and probabilistic loops, DEER subordinates LLMs to a rigid,
code-defined execution pipeline.

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

Most agent frameworks suffer from **"Prompt Drift"**: a single word change in a system prompt can break the entire
logic. DEER replaces probabilistic "vibes" with a **Deterministic Execution Engine**.

* **Execution over Prompts:** Behavior is defined by a rigid pipeline of validated tool calls, not by massive, fragile
  text prompts.
* **Typed Contracts:** Every tool uses Pydantic models for input and output, ensuring zero hallucinated arguments.
* **Multi-Layered Security:** Combines a filesystem jail with an AST-whitelist sandbox to block dangerous code
  injection.
* **Evidence-Based Verification:** The agent doesn't just "claim" success; it executes a separate verification plan to
  physically prove the goal was achieved.

> **No Arbitrary Execution**  
> Unlike traditional agents that may attempt to write and execute raw code, DEER strictly forbids arbitrary execution.
> An agent's capabilities are defined programmatically through its Tool Registry. If a capability is not explicitly
> defined as a Tool, it does not exist for the agent. This ensures that the model can only interact with the world
> through secure, typed, and validated interfaces.

---

## The DEER Workflow: Code-First Implementation

### 1. Define your Deterministic Agent's Identity

```python
from pathlib import Path
from deer.core.agent import DeterministicAgent
from deer.core.memory import VectorMemory
from deer.drivers import OllamaDriver
from deer.tools import ToolRegistry, Preset

# Infrastructure
driver = OllamaDriver(model_name="llama3")
memory = VectorMemory(path="./agent_memory")
registry = ToolRegistry()
registry.register(Preset.CODE_REPAIR | Preset.CODE_EDITOR | Preset.DATA_ANALYST)

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

### 2. Assemble your Tool Registry

```python
from deer.tools.registry import ToolRegistry
from deer.tools.builtin import FileManager, GitManager, SearchManager

tool_registry = ToolRegistry()

# Add specialized capabilities with zero-config
tool_registry.register(
    FileManager(),
    GitManager(),
    SearchManager(),
)
```

### 3. Create Custom Tools with Pydantic Validation

```python
from deer.tools import ToolProvider, tool
from deer.tools.schemas import Return


class MyCustomProvider(ToolProvider):
    @tool(modifies_state=True)
    def deploy_module(self, name: str, version: str) -> Return(status=str, job_id=int):
        """Deploys a specific python module to the internal repo."""
        # Your deterministic logic here
        return {"status": "success", "job_id": 12345}
```

---

## Built-in Deterministic Agents

The framework includes pre-configured **Deterministic Agents** in the `deer/builtins/` directory. These serve as both
ready-to-use tools and reference implementations for building your own specialized architects and managers.

---

## Technical Differentiation

| Feature            | Traditional Frameworks (LangChain, etc.) | **DEER Deterministic Agents**                    |
|:-------------------|:-----------------------------------------|:-------------------------------------------------|
| **Execution Flow** | Probabilistic (LLM decides next step)    | **Deterministic** (Plan-Validate-Execute-Verify) |
| **Tool Arguments** | Often Hallucinated                       | **Strictly Typed** (Pydantic Models)             |
| **Security**       | None / Manual                            | **Built-in Jail + AST-Whitelist Sandbox**        |
| **Debugging**      | Black box / Tricky logs                  | **Step-by-Step Execution Trace Replay**          |
| **Output**         | Raw Text                                 | **Validated & Humanized Synthesis**              |
| **Memory**         | Static Window / Basic RAG                | **Adaptive** (Popularity-Aware & Auto-Pruning)   |

---

## The "Assembly Line" Lifecycle

A **Deterministic Agent** in DEER processes requests through a linear production line:

1. **Context Retrieval:** The agent queries the popularity-aware vector memory for the most relevant knowledge.
2. **Planning:** A structured JSON pipeline is generated, specifying tool calls and expected return types.
3. **Static Validation:** The `PlanValidator` audits the plan for type-safety and reference integrity.
4. **Jailed Execution:** Tools are executed in a secure sandbox with AST-whitelisted logical expressions.
5. **Evidence Verification:** A separate, read-only plan is executed to physically confirm the goal was achieved.
6. **Synthesis:** The `ExecutionTrace` is analyzed to provide a final, human-readable professional conclusion.

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