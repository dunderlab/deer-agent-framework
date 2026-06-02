# DEER: Deterministic Executable Engine for Runtime Agents

### **Stop building "Vibe-based" Agents. Start Engineering Deterministic Agents.**

**DEER** is the first framework designed for building **Deterministic Agents** in production environments where "it usually works" isn't good enough. While other frameworks rely on massive system prompts and probabilistic loops, DEER subordinates LLMs to rigid, code-defined software structures.

[![License](https://img.shields.io/badge/license-BSD--2--Clause-blue.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)

---

## Why DEER?

Most agent frameworks suffer from **"Prompt Drift"**: you change one word in a system prompt and the whole logic breaks. DEER replaces "vibes" with **Deterministic Agents** powered by **Code Contracts**.

*   **Logic over Prompts:** Define your **Deterministic Agent**'s behavior in Python, not in a 2000-word text file.
*   **Typed Tooling:** Every tool has a Pydantic-validated input and output. No more "hallucinated" arguments.
*   **Jailed by Design:** Built-in filesystem sandboxing (Jail) ensures your **Deterministic Agent** can't escape its directory.
*   **Verification Loops:** The agent doesn't just "execute"; it validates the result against the original goal using deterministic traces.

---

## The DEER Workflow: Code-First Implementation

### 1. Define your Deterministic Agent's Identity
Forget about telling the AI to "act like a specialist." Define a high-level `DeterministicAgent` with clear boundaries and a specific tool registry.

```python
from pathlib import Path
from deer.core.agent import DeterministicAgent
from deer.drivers import get_driver_from_parser
from .tools import registry

agent = DeterministicAgent(
    description="Python Architecture Specialist",
    identity=(
        "You are a Principal Python Architect. You possess authoritative expertise "
        "in advanced module resolution and dependency management."
    ),
    driver=get_driver_from_parser(),
    registry=registry,
    jail_path=Path.cwd() / "sandbox", # Strict security boundary
    format_response="markdown",
    max_tries_for_plan=5
)

if __name__ == "__main__":
    agent.repl() # Instant interactive shell
```

### 2. Assemble your Tool Registry
Combine built-in managers (File, Git, Search) into a single, cohesive unit of execution for your **Deterministic Agent**.

```python
from deer.tools.registry import ToolRegistry
from deer.tools.builtin import FileManager, GitManager, SearchManager

registry = ToolRegistry()

# Add specialized capabilities with zero-config
registry.register(
    FileManager(),
    GitManager(),
    SearchManager(),
)
```

### 3. Create Custom Tools with Pydantic Validation
Extending your **Deterministic Agent** is as simple as writing a class. The `@tool` decorator automatically generates the JSON schema for the LLM, ensuring perfect compatibility.

```python
from deer.tools import ToolProvider, tool, Return

class MyCustomProvider(ToolProvider):
    @tool(modifies_state=True)
    def deploy_module(self, name: str, version: str) -> Return(status=str, job_id=int):
        """Deploys a specific python module to the internal repo."""
        # Your deterministic logic here
        return {"status": "success", "job_id": 12345}
```

---

## Built-in Deterministic Agents

The framework includes pre-configured **Deterministic Agents** in the `deer/builtins/` directory. These serve as both ready-to-use tools and reference implementations for building your own specialized architects and managers.

---

## Technical Differentiation

| Feature | Traditional Frameworks (LangChain, etc.) | **DEER Deterministic Agents** |
| :--- | :--- | :--- |
| **Execution Flow** | Probabilistic (LLM decides next step) | **Deterministic** (Backend-validated Plan) |
| **Tool Arguments** | Often Hallucinated | **Strictly Typed** (Pydantic Models) |
| **Security** | None / Manual | **Built-in Jail (Sandbox)** |
| **Debugging** | Black box / Tricky logs | **Step-by-Step Trace Replay** |
| **Output** | Raw Text | **Validated & Humanized Data** |

---

## The "Assembly Line" Lifecycle

A **Deterministic Agent** in DEER doesn't just "chat". It processes requests through a linear production line:

1.  **Refinement:** The **Deterministic Agent** improves the user's goal for technical clarity.
2.  **Planning:** The agent generates a complete JSON pipeline *before* executing anything.
3.  **Static Analysis:** The `PlanValidator` checks the plan for cycles or type mismatches.
4.  **Jailed Execution:** Tools run inside a secure sandbox.
5.  **Verification:** A secondary "judge" loop confirms the result matches the goal.

---

## Installation

```bash
pip install git+https://github.com/dunderlab/deer-agent-framework.git
```

*Requires Python 3.12+ and a valid LLM API Key (Gemini, Ollama, etc.).*

---

## License
Licensed under the **BSD 2-Clause License**. See [LICENSE](LICENSE) for details.

---
**Built for developers who trust code, not prompts.**
