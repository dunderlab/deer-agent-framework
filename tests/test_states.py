from deer.states import ParallelGitStateManager

path = "/Users/yeison/Development/DEER/sandbox/root"
state = ParallelGitStateManager()

state.set_reference_state(path)

state.rollback_to_previous_state()
state.purge_engine()
