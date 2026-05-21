GOAL_VERIFIER_PROMPT = """
Your ONLY task is to RETRIEVE EVIDENCE to verify this goal: '{goal}'.

1. Use tools to read files, check statuses, or get data.
2. Return the raw data retrieved as the final output.
3. DO NOT perform complex logic; just fetch the data.
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
