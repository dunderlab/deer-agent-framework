from deer.core import DeterministicAgent
import shutil


class AgentRunner:

    def __init__(self, agent: DeterministicAgent):
        self.agent = agent

    def run_goal(self, goal: str, repetitions: int):

        for i in range(repetitions):

            print(f"Working on iteration: {i+1}/{repetitions}")
            self.agent.clear_traces()
            self.agent.clear_agent_history()
            self.clear_working_dir()
            self.agent.run(goal)
            self.agent.save_trace()

    def clear_working_dir(self):

        for item in self.agent.working_dir.iterdir():
            if item.name.startswith("."):
                continue

            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()
