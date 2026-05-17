import json
import logging

from deer.schema.io import AgentInput
from deer.tools.registry import ToolRegistry
from deer.drivers.base_driver import LLMDriver
from deer.schema.plan import Plan

from .prompts import BASE_PLANNER_PROMPT, GOAL_IMPROVEMENT_PROMPT


class Planner:

    def __init__(
        self,
        identity: str,
        driver: LLMDriver | None = None,
        registry: ToolRegistry | None = None,
        format_response: str = "plain",
    ):
        self._llm_driver = driver
        self._registry = registry
        self._identity = identity
        self._format_response = format_response

    def plan(self, agent_input: AgentInput) -> Plan:
        self._improve_goal(agent_input=agent_input)
        return self._llm_driver.generate(
            prompt=self._build_prompt(agent_input),
            response_model=Plan,
        )

    def _improve_goal(self, agent_input: AgentInput):
        goal = self._llm_driver.generate(
            prompt=GOAL_IMPROVEMENT_PROMPT.format(
                identity=self._identity,
                goal=agent_input.goal,
            ),
        )
        agent_input.goal = goal

    def _build_prompt(self, agent_input: AgentInput) -> str:
        tools = self._format_available_tools()
        logging.info("Available tools:")
        logging.info(tools)

        return BASE_PLANNER_PROMPT.format(
            identity=self._identity,
            goal=agent_input.goal,
            payload=json.dumps(agent_input.payload, ensure_ascii=False),
            tools=tools,
            format_response=self._format_response,
        )

    def _format_available_tools(self) -> str:
        if self._registry is None:
            return "- No tools are available."

        return self._registry.describe()
