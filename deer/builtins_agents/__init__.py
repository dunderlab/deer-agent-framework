import os
from pathlib import Path

agents = {
    "deer-introspection": Path(__file__).parent / "deer-introspection" / "agent.py",
    "operating-system": Path(__file__).parent / "operating-system" / "agent.py",
    "python-architect": Path(__file__).parent / "python-architect" / "agent.py",
    "python-syntax-specialist": Path(__file__).parent
    / "python-syntax-specialist"
    / "agent.py",
    "base": Path(__file__).parent / "base" / "agent.py",
}
