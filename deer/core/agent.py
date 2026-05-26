import logging
import json
import re
import pickle
from typing import Callable
from datetime import datetime

from deer.prompts import (
    RESPONSE_IMPROVEMENT_PROMPT,
    ERROR_EXPLAIN_PROMPT,
    HUMANIZER_PROMPT,
    GOAL_VERIFIER_PROMPT,
    VERIFIER_JUDGE_PROMPT,
    PLANNER_PROMPT,
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
        rollback: Callable = None,
    ) -> None:
        assert format_response in {"markdown", "plaintext"}

        self.identity = identity
        self.driver = driver
        self.registry = registry or default_registry()

        self.executor = Executor(
            registry=self.registry,
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

        assert (
            max_tries_for_plan > 0
        ), f"max_tries_for_plan must be positive, got {max_tries_for_plan}"
        self.max_tries_for_plan = max_tries_for_plan

        self.history = []
        self.trace = []
        self.rollback_function = rollback
        # self.plan = None
        # self.validation_plan = None

        logger.info(f"DEER - Deterministic Executable Engine for Runtime-agents")
        logger.info(
            f"Initialized DeterministicAgent with '{self.driver.model_name}' model"
        )
        logger.info(f"Identity: {self.identity}")
        logger.info(f"Available tools:\n{self.registry.describe(read_only=False)}")

    def execute_plan(
        self,
        agent_input: AgentInput,
        feedback: {},
        read_only: bool = False,
    ):
        last_error_message = ""

        try:
            plan = self.planner.plan(agent_input, feedback, read_only=read_only)
        except Exception as planning_error:
            logger.warning(f"Planning error: {planning_error}")
            feedback = {"Planning error": str(planning_error)}
            last_error_message = str(planning_error)
            return None, feedback, last_error_message, None
        logger.info(f"Plan generated")
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
            logger.warning(f"Verification error: {validation_error}")
            feedback = {"verification error": str(validation_error)}
            last_error_message = str(validation_error)
            return None, feedback, last_error_message, plan
        logger.info(f"Plan verified")

        try:
            response = self.executor.execute(
                plan,
                agent_input.payload,
            )
        except Exception as execution_error:
            logger.warning(f"Execution error: {execution_error}")
            feedback = {"execution error": str(execution_error)}
            last_error_message = str(execution_error)
            return None, feedback, last_error_message, plan
        logger.info(f"Plan executed")

        return response, feedback, last_error_message, plan

    def run(self, agent_input: AgentInput) -> AgentOutput:

        feedback = {}
        run_trace = {}

        for attempt_idx in range(self.max_tries_for_plan):
            logger.debug(f"Attempt {attempt_idx + 1} of {self.max_tries_for_plan}")

            run_trace[f"Attempt-{attempt_idx + 1}"] = {}

            for solution_idx in range(self.max_tries_for_plan):
                logger.debug(
                    f"Solution planning {solution_idx + 1} of {self.max_tries_for_plan}"
                )
                run_trace[f"Attempt-{attempt_idx + 1}"][
                    f"Solution-{solution_idx + 1}"
                ] = datetime.now()

                response, feedback, last_error_message, plan = self.execute_plan(
                    agent_input, feedback
                )
                if response is None:
                    continue
                break

            if response is None:
                logger.warning(
                    f"Agent failed to produce a response after {self.max_tries_for_plan} attempts"
                )
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
            for verification_idx in range(self.max_tries_for_plan):
                logger.debug(
                    f"Verification planning {verification_idx + 1} of {self.max_tries_for_plan}"
                )
                run_trace[f"Attempt-{attempt_idx + 1}"][
                    f"Verification-{verification_idx + 1}"
                ] = datetime.now()

                agent_verifier_input = AgentInput(
                    goal=goal_verifier_prompt, payload=payload_verifier
                )
                response_validation, feedback_, _, validation_plan = self.execute_plan(
                    agent_verifier_input, feedback_, read_only=True
                )
                if response_validation is None:
                    continue
                break

            if response_validation is None:
                logger.warning(
                    f"Agent failed to verificate after {self.max_tries_for_plan} attempts"
                )
            else:
                response.validated, validation_feedback = self.validated(
                    response_validation
                )
                if response.validated:
                    break
                else:
                    feedback = {"Validation feedback": validation_feedback}
                    continue

            self.rollback()

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

        self.trace.append(
            {
                "execution_summary": run_trace,
                "solution_trace": response.trace,
                "verification_trace": response_validation.trace,
            }
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
                self.pretty_print(f"    {output.text}\n\n")

    def send(self, msg):
        user_input = AgentInput(
            goal=msg,
            payload={
                "history": self.history,
            },
        )
        response = self.run(user_input)

        if isinstance(response.result, dict):
            response.result = self.humanize_result(response)
        else:
            response.result = self.improve_result(response)
        return response

    def pretty_print(self, out: str):
        console = Console()
        console.print(Markdown(out))

    def clear_history(self):
        self.history = []
        self.trace = []

    def rollback(self):
        logger.debug(f"Rolling back agent")
        if self.rollback_function:
            self.rollback_function()
        else:
            logger.debug(f"No rollback function defined")

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
        logger.debug(f"Humanized response: {result_humanized}")
        return result_humanized

    def improve_result(self, response: str) -> str:
        improve_prompt = RESPONSE_IMPROVEMENT_PROMPT.format(
            format_response=self.planner.format_response,
            response=response.text,
        )
        result_improved = self.driver.generate_text(improve_prompt)
        logger.debug(f"Improved response: {result_improved}")
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
        else:
            logger.info(f"Validated")

        return is_valid, feedback

    def generate_chat_log(
        self,
        chain_messages: list[str],
        print_chat: bool = False,
        save_log: str = None,
    ):
        file_handler = None
        if save_log:
            formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
            file_handler = logging.FileHandler(save_log)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

        try:
            for i, message in enumerate(chain_messages, start=1):
                logger.debug(f"[REQUEST {i}]: '{message}'")
                if print_chat:
                    print(f">>> {message}")
                response = self.send(message)
                logger.debug(f"[RESPONSE {i}]: '{response.text}'")
                if print_chat:
                    print(f"    {response.text}")
        finally:
            if file_handler:
                logger.removeHandler(file_handler)
                file_handler.close()

    def save_trace(self, filename: str):
        obj = {
            "tools": list(self.registry.list_tools()),
            "trace": self.trace,
            "history": self.history,
        }

        if not filename.endswith(".trace"):
            filename = f"{filename}.trace"

        with open(filename, "wb") as f:
            pickle.dump(obj, f)
