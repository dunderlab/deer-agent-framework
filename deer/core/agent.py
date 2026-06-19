import logging
import json
import re
import pickle
import sys
from typing import Callable
from datetime import datetime
import os
import subprocess

from prompt_toolkit import prompt
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import InMemoryHistory
from rich.console import Console
from rich.markdown import Markdown

from deer.prompts import (
    RESPONSE_IMPROVEMENT_PROMPT,
    ERROR_EXPLAIN_PROMPT,
    HUMANIZER_PROMPT,
    GOAL_VERIFIER_PROMPT,
    VERIFIER_JUDGE_PROMPT,
)
from deer import __version__
from deer.drivers.base_driver import LLMDriver
from deer.planner.planner import Planner
from deer.validator.plan_validator import PlanValidator
from deer.executor.executor import Executor
from deer.core.ui import WELCOME_MESSAGE
from deer.tools.registry import ToolRegistry, default_registry
from deer.schema.io import AgentInput, AgentOutput
from deer.states import BaseStateManager

logger = logging.getLogger("DEER")
prompt_history = InMemoryHistory()


class DeterministicAgent:
    def __init__(
        self,
        description: str = "",
        identity: str = "DeterministicAgent",
        max_retries: int = 3,
        driver: LLMDriver | None = None,
        tool_registry: ToolRegistry | None = None,
        format_response: str = "plaintext",
        state_manager: BaseStateManager = None,
        jail_path: str = None,
    ) -> None:
        assert format_response in {"markdown", "plaintext"}

        self.identity = identity
        self.description = description
        self.driver = driver

        if isinstance(tool_registry, set):
            tr = ToolRegistry()
            tr.register(*[tool() for tool in tool_registry])
            tool_registry = tr

        self.tool_registry = tool_registry or default_registry()

        self.console = Console()

        self.executor = Executor(
            tool_registry=self.tool_registry,
        )

        self.validator = PlanValidator(
            tool_registry=self.tool_registry,
        )

        self.planner = Planner(
            identity=identity,
            driver=driver,
            tool_registry=self.tool_registry,
            format_response=format_response,
        )

        self.state_manager = state_manager

        assert (
            max_retries > 0
        ), f"max_tries_for_plan must be positive, got {max_retries}"
        self.max_retries = max_retries

        self.history = []
        self.trace = []

        if jail_path:
            self.set_jail(jail_path)

        logger.info(f"DEER - Deterministic Executable Engine for Runtime-agents")
        logger.info(
            f"Initialized DeterministicAgent with '{self.driver.model_name}' model"
        )
        logger.info(f"Identity: {self.identity}")
        logger.info(
            f"Available tools:\n{self.tool_registry.describe(include_state_modifying=True)}"
        )
        logger.info(f"Authorized filesystem scope is restricted to: {jail_path}")

    def set_jail(self, jail_path):
        self.tool_registry.set_jail(jail_path)

    def should_verify(self, plan) -> bool:
        return any(step.tool for step in plan.steps)

    def execute_plan(
        self,
        agent_input: AgentInput,
        feedback: {},
        include_state_modifying: bool = True,
    ):
        last_error_message = ""

        try:
            plan = self.planner.plan(
                agent_input,
                feedback,
                include_state_modifying=include_state_modifying,
            )
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
        response_validation = None
        last_error_message = None

        self.state_snapshot()

        for attempt_idx in range(self.max_retries):
            self.state_restore()

            logger.debug(f"Attempt {attempt_idx + 1} of {self.max_retries}")

            run_trace[f"Attempt-{attempt_idx + 1}"] = {}

            for solution_idx in range(self.max_retries):
                self.state_restore()

                logger.debug(
                    f"Solution planning {solution_idx + 1} of {self.max_retries}"
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
                    f"Agent failed to produce a response after {self.max_retries} attempts"
                )
                if last_error_message:
                    feedback = {"Previous Error": last_error_message}
                continue

            if not self.should_verify(plan):
                break

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
            for verification_idx in range(self.max_retries):
                logger.debug(
                    f"Verification planning {verification_idx + 1} of {self.max_retries}"
                )
                run_trace[f"Attempt-{attempt_idx + 1}"][
                    f"Verification-{verification_idx + 1}"
                ] = datetime.now()

                agent_verifier_input = AgentInput(
                    goal=goal_verifier_prompt, payload=payload_verifier
                )
                response_validation, feedback_, _, validation_plan = self.execute_plan(
                    agent_verifier_input, feedback_, include_state_modifying=False
                )

                if response_validation:
                    response.validated, validation_feedback = self.validated(
                        response_validation
                    )

                    if response.validated:
                        break
                    else:
                        feedback_ = {"Validation feedback": validation_feedback}
                        continue
                else:
                    continue

            if response_validation is None:
                logger.warning(
                    f"Agent failed to verificate after {self.max_retries} attempts"
                )
                continue

            if response.validated:
                break

        if response is None:
            logger.warning(
                f"Agent failed to produce a response after {self.max_retries} attempts"
            )
            if last_error_message:
                last_error_message_explained = self.explain_error(last_error_message)
            return AgentOutput(
                result=last_error_message_explained,
                trace=self.executor.trace_store.get_trace(),
            )

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
                "verification_trace": (
                    response_validation.trace if response_validation else ""
                ),
            }
        )

        self.planner.goal = agent_input.goal
        self.state_purge_engine()
        return response

    def send(self, message, print_chat: bool = False):
        user_input = AgentInput(
            goal=message,
            payload={
                "chat_history": self.history,
            },
        )

        if print_chat:
            print(f">>> {message}")

        response = self.run(user_input)
        if isinstance(response.result, dict):
            response.result = self.humanize_result(response)
        else:
            response.result = self.improve_result(response)

        if print_chat:
            print(f"    {response.result}")

        return response

    def pretty_print(self, out: str):
        self.console.print(Markdown(out))

    def clear_history(self):
        self.history = []
        self.trace = []

    def state_snapshot(self):
        if self.state_manager:
            self.state_manager.set_reference_state(self.tool_registry.jail_path)

    def state_restore(self):
        if self.state_manager:
            self.state_manager.rollback_to_previous_state()

    def state_purge_engine(self):
        if self.state_manager:
            self.state_manager.purge_engine()

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
            error=error, tools=self.tool_registry.describe()
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
            logger.info(f"Attempt validated successfully")

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
            "tools": list(self.tool_registry.list_tools()),
            "trace": self.trace,
            "history": self.history,
        }

        if not filename.endswith(".trace"):
            filename = f"{filename}.trace"

        with open(filename, "wb") as f:
            pickle.dump(obj, f)

    def show_welcome(self):
        self.console.clear()
        self.pretty_print(WELCOME_MESSAGE.format(version=__version__))
        self.pretty_print(
            f">**Agent Profile**  \n"
            f"*{self.description}*  \n"
            f"root: {self.tool_registry.jail_path}  \n"
            f"{self.driver}: {self.driver.model_name}  \n"
        )
        print("\n")

    def repl(self):
        logger.setLevel(logging.CRITICAL)
        self.show_welcome()

        while True:
            try:  # KLEEP THIS DAMM TRY
                msg = prompt(
                    HTML("<ansicyan><b>&gt;&gt;&gt; </b></ansicyan>"),
                    history=prompt_history,
                )
            except KeyboardInterrupt:
                continue
            except EOFError:
                break

            msg = msg.strip()
            if not msg:
                continue

            match msg:
                case "/exit":
                    sys.exit(0)

                case "/clear":
                    self.clear_history()
                    self.console.clear()
                    self.pretty_print(f">**Agent Profile**  \n*{self.description}*")
                    print("\n")

                case "/tools":
                    self.pretty_print(
                        self.tool_registry.describe(
                            include_state_modifying=True, markdown=True
                        )
                    )
                    print("\n")

                case "/rollback":
                    self.state_restore()
                    self.pretty_print(
                        "**Rollback executed.** System reverted to the last stable state."
                    )
                    print("\n")

                case command if command.endswith(";"):
                    # Remove the ';' from the start to get only the command
                    cmd_to_run = command[:-1].strip()

                    try:
                        # Execute the command
                        result = subprocess.run(
                            cmd_to_run,
                            shell=True,
                            capture_output=True,
                            text=True,
                            check=True,
                        )
                        print(result.stdout)
                    except subprocess.CalledProcessError as e:
                        print(f"Error executing command: {e.stderr}")
                    except Exception as e:
                        print(f"An unexpected error occurred: {e}")

                case _:
                    if msg.startswith("/"):
                        continue
                    with self.console.status(
                        "[dim]processing request[/]",
                        spinner="point",
                        spinner_style="dim",
                    ):
                        try:
                            output = self.send(msg)
                            self.pretty_print(f"    {output.text}")

                            print("\n")
                        except KeyboardInterrupt:
                            self.console.print("[dim]Interrupted. Continuing...[/]\n")
                            self.state_restore()
                            continue
                        except EOFError:
                            break

    def iterate_debug(
        self,
        chain_messages: list[str],
        repetitions: int,
        path: str,
        callback: Callable = None,
    ):
        logger.setLevel(logging.DEBUG)
        os.makedirs(path, exist_ok=True)
        # logging.info("Starting debug mode:\n")
        # logging.info("Tools:")
        # logger.info(self.tool_registry.describe(include_state_modifying=True))
        for i in range(repetitions):
            self.clear_history()
            name = f"{self.driver.model_name}-{datetime.now().timestamp()}"

            formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
            file_handler = logging.FileHandler(f"{path}/{name}.log")
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
            logger.info("Starting debug mode")
            logger.info(f"Model: {self.driver.model_name}")
            logger.info("Tools:")
            logger.info(self.tool_registry.describe(include_state_modifying=True))
            logger.removeHandler(file_handler)
            file_handler.close()

            self.generate_chat_log(
                chain_messages,
                print_chat=True,
                save_log=f"{path}/{name}.log",
            )
            self.save_trace(f"{path}/{name}.trace")
            if callback:
                callback()

    #
    # def iterate_debug(
    #     self,
    #     chain_messages: list[str],
    #     repetitions: int,
    #     path: str,
    #     callback: Callable[[], None] = None,
    # ) -> None:
    #     logger.setLevel(logging.DEBUG)
    #     os.makedirs(path, exist_ok=True)
    #
    #     session_name = f"{self.driver.model_name}-{datetime.now().timestamp()}"
    #     log_file_path = f"{path}/{session_name}_session.log"
    #
    #     formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    #     file_handler = logging.FileHandler(log_file_path)
    #     file_handler.setFormatter(formatter)
    #     logger.addHandler(file_handler)
    #
    #     logger.info("Starting debug mode")
    #     logger.info("Tools:")
    #     logger.info(self.tool_registry.describe(include_state_modifying=True))
    #
    #     logger.removeHandler(file_handler)
    #     file_handler.close()
    #
    #     for i in range(repetitions):
    #         self.clear_history()
    #
    #         self.generate_chat_log(
    #             chain_messages,
    #             print_chat=True,
    #             save_log=log_file_path,
    #         )
    #
    #         if callback:
    #             callback()
    #
    #         self.save_trace(f"{path}/{session_name}_iter_{i}.trace")
