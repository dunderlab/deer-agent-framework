from deer.tools.registry import ToolRegistry
from deer.tools.builtin import FileManager

registry = ToolRegistry()

fileManager = FileManager(
    jail="/Users/yeison/Development/deer-agent-framework/sandbox/root",
    # tools=[
    #     "new_file",
    #     "read_file",
    #     "delete_file",
    #     "create_directory",
    #     "get_file_info",
    #     "directory_tree",
    # ],
)

registry.register(
    fileManager,
)
