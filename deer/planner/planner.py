import json

from deer.prompts import PLANNER_PROMPT, GOAL_IMPROVEMENT_PROMPT
from deer.schema.io import AgentInput
from deer.tools.registry import ToolRegistry
from deer.drivers.base_driver import LLMDriver
from deer.schema.plan import Plan


class Planner:

    def __init__(
        self,
        identity: str,
        driver: LLMDriver | None = None,
        registry: ToolRegistry | None = None,
        format_response: str = "plain",
        improve_goal: bool = True,
    ):
        self.llm_driver = driver
        self.registry = registry
        self.identity = identity
        self.format_response = format_response
        self.improve_goal = improve_goal

        self.goal = ""

    def plan(self, agent_input: AgentInput, feedback={}) -> Plan:
        if self.improve_goal:
            self.run_improve_goal(agent_input=agent_input)
        plan_prompt = self.build_prompt(agent_input, feedback)
        plan = self.llm_driver.generate_json(plan_prompt, response_model=Plan)
        return plan

    def run_improve_goal(self, agent_input: AgentInput):
        goal_prompt = GOAL_IMPROVEMENT_PROMPT.format(
            identity=self.identity,
            goal=agent_input.goal,
        )
        improved_goal = self.llm_driver.generate_text(goal_prompt)
        agent_input.goal = improved_goal
        self.goal = improved_goal

    def build_prompt(self, agent_input: AgentInput, feedback={}) -> str:
        # As usable data must be JSON consistent.
        payload = json.dumps(agent_input.payload.update(feedback), ensure_ascii=False)

        planner_prompt = PLANNER_PROMPT.format(
            identity=self.identity,
            goal=agent_input.goal,
            payload=payload,
            tools=self.registry.describe(),
            format_response=self.format_response,
        )
        return planner_prompt
