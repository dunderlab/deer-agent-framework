import logging
import json
import re

from deer.prompts import (
    RESPONSE_IMPROVEMENT_PROMPT,
    ERROR_EXPLAIN_PROMPT,
    HUMANIZER_PROMPT,
    GOAL_VERIFIER_PROMPT,
    VERIFIER_JUDGE_PROMPT,
)
from deer.drivers.base_driver import LLMDriver
from deer.planner.planner import Planner
from deer.validator.plan_validator import PlanValidator
from deer.executor.executor import Executor
from deer.tools.registry import ToolRegistry, default_registry
from deer.tracing.store import TraceStore
from deer.schema.io import AgentInput, AgentOutput

from rich.console import Console
from rich.markdown import Markdown

logger = logging.getLogger("DEER")


class DeterministicAgent:
    def __init__(
        self,
        identity: str = "DeterministicAgent",
        max_tries_for_plan: int = 3,
        driver: LLMDriver | None = None,
        registry: ToolRegistry | None = None,
        format_response: str = "plaintext",
    ) -> None:
        assert format_response in {"markdown", "plaintext"}

        self.registry = registry or default_registry()
        self.trace_store = TraceStore()

        self.executor = Executor(
            registry=self.registry,
            trace_store=self.trace_store,
        )

        self.validator = PlanValidator(
            registry=self.registry,
        )

        self.planner = Planner(
            identity=identity,
            driver=driver,
            registry=self.registry,
            format_response=format_response,
        )

        self.driver = driver

        assert (
            max_tries_for_plan > 0
        ), f"max_tries_for_plan must be positive, got {max_tries_for_plan}"
        self.max_tries_for_plan = max_tries_for_plan

        self.history = []

        logger.debug(f"Initialized DeterministicAgent with '{driver.model_name}' model")
        logger.debug(f"Identity: {identity}")
        logger.debug(f"Available tools:\n{registry.describe()}")

    def execute_plan(
        self,
        agent_input: AgentInput,
        feedback: {},
    ):
        last_error_message = ""

        try:
            plan = self.planner.plan(agent_input, feedback)
        except Exception as planning_error:
            logger.error(f"Plannig error: {planning_error}")
            feedback = {"Planning error": planning_error}
            last_error_message = str(planning_error)
            return None, feedback, last_error_message, None
        logger.debug(f"Plan generated")

        logger.debug(f"Plan steps:")
        for step in plan.steps:
            logger.debug(f"\tstep: {step.id}")
            if step.tool:
                logger.debug(f"\t\ttool: {step.tool}: {step.params}")
            elif step.logic:
                logger.debug(f"\t\tlogic: {step.logic}")

        try:
            self.validator.validate(plan)
        except Exception as validation_error:
            logger.error(f"Validation error: {validation_error}")
            feedback = {"validation error": validation_error}
            last_error_message = str(validation_error)
            return None, feedback, last_error_message, plan
        logger.debug(f"Plan validated")

        try:
            response = self.executor.execute(
                plan,
                agent_input.payload,
            )
        except Exception as execution_error:
            logger.error(f"Execution error: {execution_error}")
            feedback = {"execution error": execution_error}
            last_error_message = str(execution_error)
            return None, feedback, last_error_message, plan
        logger.debug(f"Plan excecuted")

        return response, feedback, last_error_message, plan

    def run(self, agent_input: AgentInput) -> AgentOutput:

        feedback = {}

        for j in range(self.max_tries_for_plan):

            for i in range(self.max_tries_for_plan):
                logger.debug(f"Planning iteration {i+1} of 3 tries")
                response, feedback, last_error_message, plan = self.execute_plan(
                    agent_input, feedback
                )
                if response is None:
                    continue
                break

            if response is None:
                logger.warning(f"Agent failed to produce a response after 3 attempts")
                if last_error_message:
                    last_error_message_explained = self.explain_error(
                        last_error_message
                    )
                return AgentOutput(
                    result=last_error_message_explained,
                    trace=self.executor.trace_store.get_trace(),
                )

            feedback_ = {}
            goal_verifier_prompt = GOAL_VERIFIER_PROMPT.format(goal=agent_input.goal)

            payload_verifier = {
                "original_goal": agent_input.goal,
                "claimed_result": response.result,
                "execution_trace": [
                    {"id": s.step_id, "tool": s.tool or "logic", "output": s.output}
                    for s in response.trace
                ],
            }
            for k in range(self.max_tries_for_plan):
                logger.debug(f"Planning verification {k + 1} of 3 tries")

                agent_verifier_input = AgentInput(
                    goal=goal_verifier_prompt, payload=payload_verifier
                )
                response_validation, feedback_, _, _ = self.execute_plan(
                    agent_verifier_input, feedback_
                )
                if response_validation is None:
                    continue
                break

            if response_validation is None:
                logger.warning(f"Agent failed to validate a execution after 3 attempts")
            else:
                response.validated, validation_feedback = self.validated(
                    response_validation
                )
                if response.validated:
                    break
                else:
                    feedback = {"Validation feedback": validation_feedback}
                    continue

        self.history.extend(
            [
                {
                    "role": "user",
                    "content": agent_input.goal,
                },
                {
                    "role": "agent",
                    "content": response.result,
                },
            ]
        )

        self.planner.goal = agent_input.goal
        return response

    def repl(self):
        while True:
            msg = input(">>> ")
            if msg == "exit":
                break

            if msg:
                output = self.send(msg)
                self.prety_print(f"    {output.result}\n\n")

    def send(self, msg):
        user_input = AgentInput(
            goal=msg,
            payload={
                "history": self.history,
            },
        )
        output = self.run(user_input)

        if isinstance(output.result, dict):
            output.result = self.humanize_result(output)
        else:
            output.result = self.improve_result(output)
        return output

    def prety_print(self, out: str):
        console = Console()
        console.print(Markdown(out))

    def clear_history(self):
        self.history = []

    def humanize_result(self, output: AgentOutput) -> str:
        trace_str = ""
        for step in output.trace:
            trace_str += f"- {step.tool or 'logic'}: {step.output}\n"

        humanize_prompt = HUMANIZER_PROMPT.format(
            goal=self.planner.goal,
            trace=trace_str,
            result=output.result,
        )

        result_humanized = self.driver.generate_text(humanize_prompt)
        logger.info(f"Humanized response: {result_humanized}")
        return result_humanized

    def improve_result(self, response: str) -> str:
        improve_prompt = RESPONSE_IMPROVEMENT_PROMPT.format(
            format_response=self.planner.format_response,
            response=response,
        )
        result_improved = self.driver.generate_text(improve_prompt)
        logger.info(f"Improved response: {result_improved}")
        return result_improved

    def explain_error(self, error: str):
        error_prompt = ERROR_EXPLAIN_PROMPT.format(
            error=error, tools=self.registry.describe()
        )
        error_explained = self.driver.generate_text(error_prompt)
        return error_explained

    def validated(self, response_validation: AgentOutput) -> bool:
        evidence_str = ""
        feedback = ""

        for step in response_validation.trace:
            evidence_str += f"- Tool: {step.tool}, Output: {step.output}\n"
        verifier_judge_prompt = VERIFIER_JUDGE_PROMPT.format(
            goal=self.planner.goal, evidence=evidence_str
        )

        response_text = self.driver.generate_text(verifier_judge_prompt)
        json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
        data = json.loads(json_match.group(0))

        is_valid = data.get("is_success", False)

        if not is_valid:
            logger.warning(f"Validation failed: {data.get('feedback')}")
            feedback = data.get("feedback")

        return is_valid, feedback
