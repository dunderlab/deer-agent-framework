GOAL_VERIFIER_PROMPT = """
f"Your ONLY task is to RETRIEVE EVIDENCE to verify this goal: '{goal}'. "
"1. Use tools to read files, check statuses or get data. "
"2. Return the raw data retrieved. "
"3. DO NOT perform complex string concatenation or matching in 'logic' steps. "
"Just fetch the data and let the final output be the raw result of your inspection."
"""

VERIFIER_JUDGE_PROMPT = """
User Goal: {goal}

Verification Evidence (Actual State):
{evidence}

Task:
Analyze the Verification Evidence. Does it prove that the User Goal was successfully completed?

Rules:
- If the evidence shows the goal is NOT met, respond with is_success: false.
- If the evidence is missing or shows an error, respond with is_success: false.
- Respond ONLY with JSON: {{"is_success": bool, "feedback": "string explaining why"}}
"""
