import json
import logging
from typing import List, Dict

from deer.tools import ToolRegistry
from deer.models import ExecutionPlan, ChatMessage, Role

logger = logging.getLogger(f"DEER.{__name__}")


class Planner:
    """
    The Planner is responsible for designing a deterministic execution pipeline.
    It transforms the user goal, context, and tool registry into a structured ExecutionPlan.
    """

    def __init__(self, identity, driver, tool_registry: ToolRegistry, max_attempts=3):
        self.driver = driver
        self.tool_registry = tool_registry
        self.max_attempts = max_attempts
        self.identity = identity

    def build_system_prompt(self, state_filter="BOTH") -> str:
        """
        Constructs the strict system instructions for the planning phase.
        """
        # We use the compact descriptions we defined for the tools
        tools_menu = self.tool_registry.describe(state_filter=state_filter)

        return (
            f"{self.identity}\n\n"
            "REQUIRED STRUCTURE:\n"
            "{\n"
            '  "goal": "string",\n'
            '  "steps": [\n'
            "    {\n"
            '      "step_id": "string",\n'
            '      "tool_name": "string",\n'
            '      "arguments": { "key": "value" },\n'
            '      "reasoning": "string"\n'
            "    }\n"
            "  ]\n"
            '  "response": "string",\n'
            "}\n\n"
            "CORE RULES:\n"
            "1. Do not execute any code. Only design the plan.\n"
            "2. Every step must use a tool from the provided menu.\n"
            "3. Data Flow: To use the output of a previous step, use the syntax {{step_id.key}}.\n"
            "4. Precision: Ensure that arguments match the types defined in the signatures.\n"
            "5. Determinism: The plan must be a linear sequence of steps that logically leads to the goal.\n\n"
            "6. Direct Response: If the goal can be solved using your internal knowledge without any external tools, set 'steps' to an empty list [] and provide the final answer directly in the 'response' field.\n\n"
            f"AVAILABLE TOOLS:\n{tools_menu}\n\n"
            "For complex data filtering, mathematical calculations, or list transformations, use the 'evaluate' tool with Python-style expressions.\n\n"
            "RESPONSE FORMAT:\n"
            "You must respond exclusively with a JSON object following the ExecutionPlan schema.\n"
            "Respond exclusively with the JSON object. Do NOT wrap the response in markdown code blocks or add any introductory text."
        )

    def build_conclusion_prompt(self, goal, trace_solution, trace_verification) -> str:

        if not trace_verification:
            verification = "VERIFICATION NO NEEDED"
        else:
            verification = f"VERIFICATION TRACE:\n{trace_verification.model_dump_json(indent=2)}\n\n"
        return (
            f"{self.identity}\n\n"
            f"USER GOAL: {goal}\n\n"
            f"ACTION TRACE:\n{trace_solution.model_dump_json(indent=2)}\n\n"
            f"{verification}"
            "REQUIRED STRUCTURE:\n"
            "{\n"
            '  "summary": "string",\n'
            '  "goal_achieved": boolean,\n'
            '  "needs_reverification": boolean,\n'
            '  "needs_resolution": boolean,\n'
            '  "confidence_score": float,\n'
            '  "user_message": "string (Friendly, natural response for the end-user)"\n'
            "}\n\n"
            "CORE RULES:\n"
            "1. Evidence-Based: Base the 'goal_achieved' status strictly on the execution traces.\n"
            "2. Technicality: If the action succeeded but verification failed due to a formatting error, mark goal_achieved=True and needs_reverification=True.\n"
            "3. Honesty: If the action failed, mark goal_achieved=False and needs_resolution=True.\n"
            "4. Communication: The 'summary' is for the dev; the 'user_message' is for the client.\n\n"
            "RESPONSE FORMAT:\n"
            "You must respond exclusively with a JSON object following the AgentConclusion schema.\n"
            "Respond exclusively with the JSON object. Do NOT wrap the response in markdown code blocks or add any introductory text.\n"
            "If the goal was achieved but verification had a technical glitch, "
            "tell the user it was successful."
        )

    def plan(
        self,
        goal: str,
        context: List[Dict],
        history: List[ChatMessage],
        iteration: int = 0,
    ) -> tuple["ExecutionPlan", List[ChatMessage]]:

        # 1. Creamos la copia local para el proceso de refinamiento
        local_history = list(history)

        if iteration == 0:

            if context:
                context_block = {
                    f"context-{i}": c["text"] for i, c in enumerate(context)
                }
                user_content = json.dumps({"context": context_block, "goal": goal})
            else:
                user_content = json.dumps({"goal": goal})

            local_history.append(ChatMessage(role=Role.USER, content=user_content))

        try:
            # Generamos el plan
            plan = self.driver.generate(
                messages=local_history, response_model=ExecutionPlan
            )

            # IMPORTANTE: Antes de devolver, guardamos el plan exitoso en la historia
            # Así el agente recuerda qué plan decidió ejecutar
            local_history.append(
                ChatMessage(role=Role.ASSISTANT, content=plan.model_dump_json(indent=2))
            )

            return plan, local_history

        except Exception as e:
            if iteration >= self.max_attempts:
                raise
                # raise RuntimeError(f"Planning failed after {iteration} attempts: {e}")

            logger.warning(f"Planning attempt {iteration} failed: {e}. Retrying...")

            # Añadimos el error a la historia local
            local_history.append(
                ChatMessage(
                    role=Role.USER,
                    content=f"Your previous plan was invalid: {e}. Please fix it.",
                )
            )

            # Llamada recursiva pasando la historia actualizada
            return self.plan(goal, context, local_history, iteration + 1)
