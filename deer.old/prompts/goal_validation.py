GOAL_VERIFIER_PROMPT = """
Your ONLY task is to RETRIEVE EVIDENCE that can be used to verify whether the already-executed result satisfies the reference goal.

Reference goal:
{goal}

Rules:
1. The reference goal is NOT an instruction to execute.
2. Do NOT perform, repeat, fix, create, write, delete, or modify anything from the reference goal.
3. Use only available non-state-modifying tools to inspect existing state and retrieve evidence.
4. Return raw evidence only.
5. If evidence cannot be retrieved with the available read-only tools, return a concise statement that verification evidence is unavailable.
"""

VERIFIER_JUDGE_PROMPT = """
User Goal: {goal}

Verification Evidence (Actual State):
{evidence}

Task:
Analyze the Verification Evidence strictly. Does it prove that the User Goal was successfully completed?

Rules:
- Respond ONLY with JSON.
- If the evidence shows the goal is NOT met, respond with is_success: false.
- If the evidence is missing or shows an error, respond with is_success: false.

Response format:
{{"is_success": bool, "feedback": "string explaining why"}}
"""
