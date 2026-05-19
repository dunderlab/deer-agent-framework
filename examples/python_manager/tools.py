from deer.tools.registry import ToolRegistry
from deer.tools.builtin import FileManager

registry = ToolRegistry()

fileManager = FileManager(
    jail="/Users/yeison/Development/deer-agent-framework/sandbox/root"
)

registry.register(
    fileManager,
)
