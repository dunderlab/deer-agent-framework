import logging
from typing import Optional, Union
from pathlib import Path

from deer.engine import Planner, PipelineExecutor, PlanValidator
from deer.engine.schemas import ExecutionTrace, AgentConclusion

from deer.drivers.schemas import Role
from deer.tools import ToolRegistry, ToolProvider


from deer.drivers import LLMDriver, ChatMessage

from deer.vector_memory import VectorMemory

logger = logging.getLogger("DEER")


class DeterministicAgent:

    def __init__(
        self,
        description: str,
        identity: str,
        driver: LLMDriver,
        tool_registry: ToolRegistry | set[ToolProvider],
        working_dir: Path,
        vector_memory: Optional[VectorMemory] = None,
        max_attempts: int = 3,
    ):
        pass

        self.agent_dir = working_dir / ".deer"

        # Context
        self.identity = identity
        self.description = description

        # LLMDriver
        self.driver = driver

        # ToolRegistry
        if isinstance(tool_registry, set):
            tr = ToolRegistry()
            tr.register(*[tool() for tool in tool_registry])
            tool_registry = tr
        self.tool_registry = tool_registry
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
        self.agent_history.append(
            ChatMessage(
                role=Role.SYSTEM,
                content=self.planner.build_system_prompt(),
            )
        )

        # Validator History
        self.validator_history: list[ChatMessage] = []
        self.clear_validator_history()

        logger.info(f"DEER - Deterministic Executable Engine for Runtime-agents")
        logger.info(
            f"Initialized DeterministicAgent with '{self.driver.model_name}' model"
        )
        logger.info(f"Identity: {self.identity}")
        logger.info(
            f"Available tools:\n{self.tool_registry.describe(state_filter='BOTH')}"
        )
        logger.info(f"Authorized filesystem scope is restricted to: {working_dir}")

    def clear_validator_history(self):
        self.validator_history = [
            ChatMessage(
                role=Role.SYSTEM,
                content=self.planner.build_system_prompt(state_filter="READ_ONLY"),
            )
        ]

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
            history=self.validator_history,
            update_history_attr="validator_history",
        )
        return trace

    def run(self, goal: str, trace_solution=None, trace_verification=None):

        if trace_solution is None:
            trace_solution = self.run_solution(goal)

        if trace_verification is None:
            trace_verification = self.run_verification(goal)

        # Conclusion
        conclusion = self.generate_conclusion(goal, trace_solution, trace_verification)

        if conclusion.goal_achieved:
            self.clear_validator_history()
            return conclusion.user_message

        if conclusion.needs_resolution:
            self.agent_history.append(
                ChatMessage(
                    role=Role.SYSTEM,
                    content=f"EXECUTION FAILURE: {conclusion.summary}. Please redesign the plan.",
                )
            )
            return self.run(goal, trace_solution=None, trace_verification=None)

        if conclusion.needs_reverification:
            self.validator_history.append(
                ChatMessage(
                    role=Role.SYSTEM,
                    content=f"VERIFICATION GLITCH: {conclusion.summary}. Retrying verification...",
                )
            )
            return self.run(
                goal, trace_solution=trace_solution, trace_verification=None
            )

        return conclusion.summary

    def generate_conclusion(
        self, goal: str, trace_solution: ExecutionTrace, trace_verification: ExecutionTrace
    ) -> str:

        messages = [
            ChatMessage(
                role=Role.SYSTEM,
                content="You are a professional technical assistant. "
                "Summarize execution results clearly.",
            ),
            ChatMessage(role=Role.USER, content=self.planner.build_conclusion_prompt(goal, trace_solution, trace_verification)),
        ]

        return self.driver.generate(messages=messages, response_model=AgentConclusion)
