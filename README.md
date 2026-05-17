# DEER - Deterministic Executable Engine for Runtime-agents

**DEER** is not an agent framework. It is a **Deterministic Orchestration and Supervision Platform** designed to subordinate Large Language Models (LLMs) to a rigid, traditional software structure.

The system acts as the operational brain, judge, and data administrator, degrading the LLM to the role of a **specialized text-processing operator**.

---

## System Identity Summary

DEER’s primary purpose is to govern the linguistic capabilities of LLMs through a deterministic backend. It treats AI as a computational tool, not a decision-making entity.

### What the System DOES (Scope & Functions)
- **Workflow Governance:** The backend dictates the start, development, and end of every process.
- **Traditional Infrastructure Management:** Deterministically controls authentication, relational database persistence, and session state.
- **Trigger-Based IA Activation:** Evaluates data flow and activates a specific agent only when natural language processing is strictly necessary.
- **Context Isolation & Specialization:** Instantiates modular agents with restrictive System Prompts that delimit roles, goals, and security rules.
- **Real-Time Data Assembly:** Meticulously builds a **3-layer payload** before every query:
    1. **Identity (Static):** The agent's core definition.
    2. **Memory (Dynamic):** Filtered conversation history.
    3. **External Data (RAG/APIs):** Live data extracted on-the-fly.
- **Mandatory Quality Control:** Every LLM response is subjected to validation, cleaning, and formatting before persisting or reaching the user.

### What the System DOES NOT (Limits & Restrictions)
- **NO "Chat Wrapper":** It does not expose a raw LLM API nor decorate a generic chat interface.
- **NO AI Governance:** The LLM does not make business logic decisions, manage application routes, or alter database states autonomously.
- **NO Generic Models:** Rejects massive "all-in-one" prompts; problems are fragmented into sub-tasks for specialized operators.
- **NO Trust in Raw Output:** Never delivers unvalidated LLM output to the user or internal systems.
- **NO Context Saturation:** Does not dump disorganized history; the orchestrator selects only the essential raw material for each request.

---

## The Request Lifecycle (Linear Assembly Line)

Every interaction follows a controlled, linear production line:

1. **CONTROL LAYER** ──► (Evaluates state, extracts RAG, assembles 3-layer payload)
2. **RESTRICTED AGENT** ──► (LLM processes text strictly within its guardrails)
3. **VALIDATION** ──────► (Backend cleans, verifies data contracts, and formats)
4. **SECURE RESULT** ────► (Data is persisted or displayed)

---

## Technical Differentiation

| Dimension | Common Bot (Wrapper) | DEER Orchestration |
| :--- | :--- | :--- |
| **Flow Control** | Probabilistic (LLM prompt governed) | **Deterministic** (Backend code governed) |
| **Data Handling** | Dumps all available text | **Structured** (Optimized 3-layer payload) |
| **Output Security** | Displays raw model output | **Validated** (Mandatory post-processing) |
| **Structure** | Single open communication channel | **Modular** ecosystem of specialized agents |

---

## Core Components

- **Planner/Orchestrator**: Generates a structured JSON plan based on rigid rules.
- **PlanValidator**: Performs static analysis of the plan *before* any tool is executed.
- **Executor**: Runs tools step-by-step according to the validated plan.
- **TraceStore**: Full auditable recording of states, plans, and results.

## Installation

```bash
pip install deer-agents
```

## Example: Defining a Specialized Tool

```python
from pydantic import BaseModel
from deer_agents.tools import Tool

class SalesInput(BaseModel):
    period: str

class SalesOutput(BaseModel):
    total: float

class FetchSales(Tool):
    input_schema = SalesInput
    output_schema = SalesOutput

    def execute(self, input: SalesInput) -> SalesOutput:
        # Business logic remains in the backend
        return SalesOutput(total=1234.56)
```

## License

MIT License
