ERROR_EXPLAIN_PROMPT = """
Execution error:
{error}

Available tools:
{tools}

Analysis task:
Determine whether the failure was caused by one of the following:

1. Missing capability
- The required operation cannot be performed because no suitable tool exists.

2. Incorrect tool selection
- A valid tool exists, but the wrong tool was selected.

3. Invalid tool usage
- A valid tool exists, but it was invoked with invalid arguments, invalid sequencing, or incompatible data.

4. Logic or execution failure
- The failure originated from executable logic, runtime behavior, or tool-side execution.

Requirements:
- Analyze the error using ONLY the available tools listed above.
- Do NOT invent capabilities that are not explicitly available.
- Explicitly state whether the system lacks the required tooling to complete the task.
- If a missing capability is detected, identify the exact missing operation.
- If a valid tool exists, identify which tool should have been used and why.
- Keep the explanation concise, deterministic, and technical.
"""
