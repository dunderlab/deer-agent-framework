from deer.core import DeterministicAgent


class AgentRunner:

    def __init__(self, agent: DeterministicAgent):
        self.agent = agent

    def run_goal(self, goal: str, repetitions: int):

        for i in range(repetitions):

            print(f"Working on iteration: {i+1}/{repetitions}")

            self.agent.clear_traces()
            self.agent.clear_agent_history()
            self.agent.clear_working_dir(ignore=[".deer", "traces"])

            self.agent.run(goal)

            self.agent.save_trace()
