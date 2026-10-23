import shutil

from deer.core import DeterministicAgent


class AgentRunner:
    """Handles the execution of a DeterministicAgent over multiple iterations to evaluate goal achievement and trace consistency."""

    def __init__(self, agent: DeterministicAgent) -> None:
        self.agent = agent

    def run_goal(self, goal: str, repetitions: int) -> None:
        """
        Executes the agent's run method for a specified goal multiple times.

        Parameters
        ----------
        goal : str
            The objective the agent is tasked to achieve.
        repetitions : int
            The number of times to repeat the execution cycle.
        """

        for i in range(repetitions):

            print(f"Working on iteration: {i+1}/{repetitions}")
            self.agent.reset_traces()
            self.agent.reset_history()
            self.clear_working_dir()
            self.agent.run(goal)
            self.agent.dump_trace()

    def clear_working_dir(self) -> None:
        """
        Removes all non-hidden files and directories from the agent's working directory.
        """

        for item in self.agent.working_dir_path.iterdir():
            if item.name.startswith("."):
                continue

            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()
