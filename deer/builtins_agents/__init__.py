import os
from pathlib import Path

agents = {
    "deer-introspection": os.path.join(
        Path(__file__).parent / "deer-introspection" / "agent.py"
    ),
    "operating-system": os.path.join(
        Path(__file__).parent / "operating-system" / "agent.py"
    ),
    "python-architect": os.path.join(
        Path(__file__).parent / "python-architect" / "agent.py"
    ),
    "python-syntax-specialist": os.path.join(
        Path(__file__).parent / "python-syntax-specialist" / "agent.py"
    ),
}
