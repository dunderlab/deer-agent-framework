import logging
import os.path
import shutil
from typing import Optional, Union, Literal
from pathlib import Path

from typing_extensions import Any
from datetime import datetime
from deer.engine import Planner, PipelineExecutor, PlanValidator
from deer.engine.schemas import ExecutionTrace, AgentConclusion

from deer.drivers.schemas import Role
from deer.tools import ToolRegistry, ToolProvider
from deer.tools.presets import LogicProvider


from deer.drivers import LLMDriver, ChatMessage

from .memory import VectorMemory


import pickle

logger = logging.getLogger("DEER")


class DeterministicAgent:

    def __init__(
        self,
        description: str,
        identity: str,
        driver: LLMDriver,
        working_dir: Path,
        tool_registry: Optional[ToolRegistry | set[ToolProvider]] = None,
        vector_memory: Optional[VectorMemory] = None,
        max_attempts: int = 3,
        enable_verification: bool = True,
    ):

        # Context
        self.identity = identity
        self.description = description
        self.max_attempts = max_attempts
        self.agent_dir = (working_dir / ".deer").resolve()
        self.working_dir = working_dir.resolve()
        self.enable_verification = enable_verification

        # LLMDriver
        self.driver = driver

        # ToolRegistry
        if isinstance(tool_registry, (set, tuple, list)):
            tr = ToolRegistry()
            tr.register(*[tool() for tool in tool_registry])
            self.tool_registry = tr
        elif tool_registry is None:
            self.tool_registry = ToolRegistry()
        elif isinstance(tool_registry, ToolRegistry):
            self.tool_registry = tool_registry

        if not self.tool_registry.has("evaluate"):
            self.tool_registry.register(LogicProvider())
        self.tool_registry.set_jail(working_dir)

        # Vector Memory
        if vector_memory:
            self.vector_memory = vector_memory
        else:
            self.vector_memory = VectorMemory(self.agent_dir / "vector_db")

        # Planner
        self.planner = Planner(
            driver=self.driver,
            tool_registry=self.tool_registry,
            max_attempts=max_attempts,
        )

        # Validator
        self.plan_validator = PlanValidator(tool_registry=self.tool_registry)

        # Pipeline Executer
        self.pipeline_executor = PipelineExecutor(tool_registry=self.tool_registry)

        # Agent History
        self.agent_history: list[ChatMessage] = []
        self.clear_agent_history()

        # Validator History
        self.verificator_history: list[ChatMessage] = []
        self.clear_verificator_history()

        # Traces
        self.traces: dict[Literal["solution", "verification"], list[Any]] = {}
        self.clear_traces()

        logger.info(f"DEER - Deterministic Executable Engine for Runtime-agents")
        logger.info(
            f"Initialized DeterministicAgent with '{self.driver.model_name}' model"
        )
        logger.info(f"Identity: {self.identity}")
        logger.info(
            f"Available tools:\n{self.tool_registry.describe(state_filter='BOTH')}"
        )
        logger.info(f"Authorized filesystem scope is restricted to: {working_dir}")

    def clear_verificator_history(self):
        self.verificator_history = [
            ChatMessage(
                role=Role.SYSTEM,
                content=self.planner.build_system_prompt(state_filter="READ_ONLY"),
            )
        ]

    def clear_agent_history(self):
        self.agent_history = [
            ChatMessage(
                role=Role.SYSTEM,
                content=self.planner.build_system_prompt(),
            )
        ]

    def save_trace(self):
        obj = {
            "tools": list(self.tool_registry.list_tools()),
            "traces": {
                "solution": self.traces["solution"],
                "verification": self.traces["verification"],
            },
            "history": self.agent_history,
        }

        filename = self.agent_dir / "traces" / f"trace-{datetime.now()}.trace"

        if not os.path.exists(os.path.dirname(filename)):
            os.mkdir(os.path.dirname(filename))

        with open(filename, "wb") as f:
            pickle.dump(obj, f)

        logger.info(f"Trace generated in {filename}")

    def clear_working_dir(self, ignore=[]):

        for item in os.listdir(self.working_dir):
            if item in ignore:
                continue

            full_path = self.working_dir / item
            if os.path.isdir(full_path):
                shutil.rmtree(full_path)
            else:
                os.remove(full_path)

    def _execute_phase(
        self, goal: str, history: list[ChatMessage], update_history_attr: str
    ) -> tuple[ExecutionTrace, list[ChatMessage]]:

        plan, updated_history = self.planner.plan(
            goal=goal,
            context=self.vector_memory.query(goal, n_results=3),
            history=history,
        )

        # Validate
        self.plan_validator.validate(plan)

        trace = self.pipeline_executor.execute(plan)
        setattr(self, update_history_attr, updated_history)
        return trace, updated_history

    def run_solution(self, goal: str) -> ExecutionTrace:
        """Executes the primary action plan to solve the goal."""
        trace, _ = self._execute_phase(
            goal=goal, history=self.agent_history, update_history_attr="agent_history"
        )
        return trace

    def run_verification(self, goal: str) -> ExecutionTrace:
        """Executes a verification plan to audit the solution."""
        verification_goal = (
            f"Verify that the following goal was successfully achieved: {goal}"
        )
        trace, _ = self._execute_phase(
            goal=verification_goal,
            history=self.verificator_history,
            update_history_attr="verificator_history",
        )
        return trace

    def save_trace_solution(self, trace_solution):
        self.traces["solution"].append(trace_solution)

    def save_trace_verification(self, trace_verification):
        self.traces["verification"].append(trace_verification)

    def clear_traces(self):
        self.traces = {"solution": [], "verification": []}

    def run(
        self,
        goal: str,
        trace_solution=None,
        trace_verification=None,
        iteration: int = 0,
    ):
        if iteration == 0:
            self.clear_verificator_history()

        if trace_solution is None:
            trace_solution = self.run_solution(goal)
            self.save_trace_solution(trace_solution)

        if (trace_verification is None) and self.enable_verification:
            trace_verification = self.run_verification(goal)
            self.save_trace_verification(trace_verification)

        # Conclusion
        conclusion = self.generate_conclusion(goal, trace_solution, trace_verification)

        if conclusion.goal_achieved:
            # self.clear_verificator_history()
            return conclusion.user_message
        else:
            if iteration >= self.max_attempts:
                return "I couldn't find a reliable way to solve this request after several attempts. Please try rephrasing your goal."

        if conclusion.needs_resolution:
            self.agent_history.append(
                ChatMessage(
                    role=Role.SYSTEM,
                    content=f"EXECUTION FAILURE: {conclusion.summary}. Please redesign the plan.",
                )
            )
            return self.run(
                goal,
                trace_solution=None,
                trace_verification=None,
                iteration=iteration + 1,
            )

        if conclusion.needs_reverification and self.enable_verification:
            self.verificator_history.append(
                ChatMessage(
                    role=Role.SYSTEM,
                    content=f"VERIFICATION GLITCH: {conclusion.summary}. Retrying verification...",
                )
            )
            return self.run(
                goal,
                trace_solution=trace_solution,
                trace_verification=None,
                iteration=iteration + 1,
            )

        return conclusion.summary

    def generate_conclusion(
        self,
        goal: str,
        trace_solution: ExecutionTrace,
        trace_verification: ExecutionTrace,
    ) -> str:

        messages = [
            ChatMessage(
                role=Role.SYSTEM,
                content="You are a professional technical assistant. "
                "Summarize execution results clearly.",
            ),
            ChatMessage(
                role=Role.USER,
                content=self.planner.build_conclusion_prompt(
                    goal, trace_solution, trace_verification
                ),
            ),
        ]

        return self.driver.generate(messages=messages, response_model=AgentConclusion)
