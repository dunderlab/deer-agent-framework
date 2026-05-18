from traceback import extract_tb

from pip._internal.utils import logging

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


class DeterministicAgent:
    def __init__(
        self,
        identity: str = "DeterministicAgent",
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

        self.history = []

    def run(self, agent_input: AgentInput) -> AgentOutput:

        try:
            feedback = {}
            for i in range(3):

                self.plan = self.planner.plan(agent_input, feedback)
                try:
                    self.validator.validate(self.plan)
                except Exception as validation_error:
                    logging.warning(f"Validation error ({i}/3): {validation_error}")
                    feedback = {"previous error": validation_error}

            response = self.executor.execute(
                self.plan,
                agent_input,
            )
        except Exception as e:
            # raise ValueError(f"Error running agent: {e}")
            return self.explain_error(e)

        self.history.append(
            {
                "role": "user",
                "content": agent_input.goal,
            }
        )

        self.history.append(
            {
                "role": "agent",
                "content": response.result,
            }
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
        output = self.improve_result(output)

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
        return result_improved

    def explain_error(self, error: str):
        error_prompt = EXPLAIN_ERROR_PROMPT.format(
            error=error, tools=self.registry.describe()
        )
        error_explained = self.driver.generate_text(error_prompt)
        return error_explained
