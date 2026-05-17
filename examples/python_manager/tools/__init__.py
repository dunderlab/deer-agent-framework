from deer.tools.registry import ToolRegistry
from .file_manager import FileManager

registry = ToolRegistry()
registry.register_methods(FileManager())
