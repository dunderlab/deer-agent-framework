import logging

from deer.drivers.base_driver import LLMDriver
from deer.planner.planner import Planner
from deer.validator.validator import PlanValidator
from deer.executor.executor import Executor
from deer.tools.registry import ToolRegistry, default_registry
from deer.tracing.store import TraceStore
from deer.schema.io import AgentInput, AgentOutput

from rich.console import Console
from rich.markdown import Markdown

from deer.planner.prompts import RESPONSE_IMPROVEMENT_PROMPT, EXPLAIN_ERROR_PROMPT

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
        self.max_tries_for_plan = max_tries_for_plan

        self.history = []

        logger.debug(
            f"Initialized DeterministicAgent with identity '{identity}' and driver '{driver.model_name}'"
        )
        logger.debug(f"Available tools:\n{registry.describe()}")

    def run(self, agent_input: AgentInput) -> AgentOutput:

        feedback = {}
        last_error_message = ""

        for i in range(self.max_tries_for_plan):
            logger.debug(f"Planning iteration {i+1} of 3 tries")
            self.plan = self.planner.plan(agent_input, feedback)
            logger.debug(f"Plan steps:")
            for step in self.plan.steps:
                logger.debug(f"\tstep: {step.id}")
                if step.tool:
                    logger.debug(f"\t\ttool: {step.tool}: {step.params}")
                elif step.logic:
                    logger.debug(f"\t\tlogic: {step.logic}")

            try:
                self.validator.validate(self.plan)
            except Exception as validation_error:
                logger.warning(f"Validation error ({i}/3): {validation_error}")
                feedback = {"validation error": validation_error}
                last_error_message = str(validation_error)
                continue
            logger.debug(f"Plan validated")

            try:
                response = self.executor.execute(self.plan, agent_input)
            except Exception as execution_error:
                response = None
                logger.warning(f"Execution error: {execution_error}")
                feedback = {"execution error": execution_error}
                last_error_message = str(execution_error)
                continue
            logger.debug(f"Plan excecuted")

            break

        if response is None:
            logger.warning(f"Agent failed to produce a response after 3 attempts")
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
        output.result = self.improve_result(output.result)
        return output

    def prety_print(self, out: str):
        console = Console()
        console.print(Markdown(out))

    def improve_result(self, response: str):
        improve_prompt = RESPONSE_IMPROVEMENT_PROMPT.format(
            format_response=self.planner._format_response,
            response=response,
        )
        result_improved = self.driver.generate_text(improve_prompt)
        logger.info(f"Improved response: {result_improved}")
        return result_improved

    def explain_error(self, error: str):
        error_prompt = EXPLAIN_ERROR_PROMPT.format(
            error=error, tools=self.registry.describe()
        )
        error_explained = self.driver.generate_text(error_prompt)
        return error_explained
