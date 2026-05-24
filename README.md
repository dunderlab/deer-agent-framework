# DEER - Deterministic Executable Engine for Runtime Agents

**DEER** is not just another agent framework. It is a **Deterministic Orchestration and Supervision Platform** designed to subordinate Large Language Models (LLMs) to a rigid, traditional software structure.

While most frameworks prioritize flexibility and rapid experimentation, DEER prioritizes **determinism, auditability, reproducibility, and production-grade execution control**.

---

## 1. The Problem & Philosophy

### Problem Statement
Current LLM agent frameworks suffer from structural weaknesses:
- **Heuristic execution:** Tool calls are often selected based on "vibes" rather than contracts.
- **Weak validation:** Plans are executed incrementally without a full formal check.
- **Opacity:** Execution traces are often incomplete or non-reproducible.
- **Lack of Control:** LLMs often control the architecture instead of the architecture controlling the LLM.

### Core Design Philosophy
1. **Structural Determinism:** Execution flow is governed by formal runtime rules, not emergent LLM behavior.
2. **Typed Tool Contracts:** Every tool must declare validated `input_schema` and `output_schema`.
3. **Plan-First Execution:** A complete JSON plan must satisfy formal validation before a single tool is executed.
4. **Separation of Responsibilities:** Architecturally isolated components for Planning, Validation, Execution, and Tracing.
5. **Full Traceability:** Every execution is recorded for deterministic replay and auditability.

---

## 2. System Identity (Scope)

DEER treats the LLM as a **specialized text-processing operator**, not a decision-making entity.

### What the System DOES
- **Workflow Governance:** Dictates the start, development, and end of every process.
- **Typed Data Flow:** Enforces strict data contracts between the LLM and your backend.
- **Context Isolation:** Instantiates modular agents with restrictive System Prompts.
- **Meticulous Payload Assembly:** Builds a **3-layer payload** (Identity, Memory, External Data) before every query.
- **Mandatory Quality Control:** Every response is validated, cleaned, and formatted before persistence.

### What the System DOES NOT
- **NO "Chat Wrapper":** It is not a generic chat interface.
- **NO Autonomous Business Logic:** The LLM does not alter database states or manage routes directly.
- **NO Trust in Raw Output:** Never delivers unvalidated LLM output to internal systems.

---

## 3. How it Works

### The Request Lifecycle (Linear Assembly Line)
Every interaction follows a controlled, linear production line:

1. **CONTROL LAYER** ──► (Evaluates state, extracts RAG, assembles 3-layer payload)
2. **RESTRICTED AGENT** ──► (LLM processes text strictly within its guardrails)
3. **VALIDATION** ──────► (Backend cleans, verifies data contracts, and formats)
4. **SECURE RESULT** ────► (Data is persisted or displayed)

### Core Components
- **Planner:** Uses an LLM to generate a structured pipeline JSON based on strict tool definitions.
- **PlanValidator:** Performs static analysis (No cycles, type compatibility, depth constraints) **before** execution.
- **Executor:** Executes tools step-by-step according to the validated plan.
- **TraceStore:** Persists the entire state transition for auditing and deterministic replay.

---

## 4. Technical Differentiation

| Dimension | Common Agent Framework | DEER Orchestration |
| :--- | :--- | :--- |
| **Flow Control** | Probabilistic (Prompt governed) | **Deterministic** (Backend governed) |
| **Data Handling** | Dumps unstructured text | **Structured** (Optimized 3-layer payload) |
| **Execution** | Incremental / Heuristic | **Plan-First** (Pre-validated) |
| **Output Security** | Displays raw model output | **Validated** (Mandatory post-processing) |

---

## 5. Use Cases

**DEER is suitable for:**
- Enterprise reporting & Automated regulatory workflows.
- Controlled data processing pipelines.
- Audit-sensitive environments requiring traceable reasoning.

**DEER is NOT optimized for:**
- Creative conversational agents.
- Rapid prototyping with flexible/vague prompts.

---

## 6. Getting Started

### Installation
```bash
pip install deer-agent-framework
```

### Example: Defining a Specialized Tool
```python

```

---

## 7. License
BSD 2-Clause License
