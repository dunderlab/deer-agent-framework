# WELCOME_MESSAGE = """
# # DEER
#
# Deterministic Executable Engine for Runtime Agents
#
# DEER is a deterministic orchestration framework for LLM-based agents focused on:
# - formal execution control
# - validated tool contracts
# - traceable execution
# - reproducible workflows
#
# Unlike conventional agent frameworks, DEER separates planning, validation, execution, and tracing into isolated runtime
# layers governed by explicit backend rules instead of emergent model behavior.
#
# ### Workflow
# DEER executes requests through a rigorous four-stage process:
# 1.  **Plan**: A structured strategy is generated to meet your goal.
# 2.  **Validate**: The plan is analyzed for logical consistency and safety.
# 3.  **Execute**: Actions are performed using verified system tools.
# 4.  **Verify**: Outcomes are cross-referenced with the initial requirements.
#
# ### Commands
# - `exit`: Terminate the current session.
# - `clear`: Clear the console.
# - `help`: List all available tools and capabilities.
# """

WELCOME_MESSAGE = """
# DEER

Deterministic Executable Engine for Runtime Agents

DEER is a deterministic orchestration framework for LLM agents focused on:
- formal execution control
- validated tool contracts
- traceable execution
- reproducible workflows

## Runtime Pipeline

1. Plan      → Generate a structured execution strategy
2. Validate  → Verify contracts, dependencies, and safety
3. Execute   → Run approved tools and workflows
4. Verify    → Validate outputs against expected objectives

## System Guarantees

- Deterministic execution flow
- Typed tool interfaces
- Structured validation layers
- Full execution traceability
- Backend-governed orchestration

## Commands

- `tools;`   → Show tools and capabilities
- `clear;`  → Clear the console
- `exit;`   → Terminate the session
"""
