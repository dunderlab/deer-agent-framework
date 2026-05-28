from deer.tools.registry import ToolRegistry
from deer.tools.builtin import FileManager, GitManager, SearchManager

jail_path = "/Users/yeison/Development/deer-agent-framework/sandbox/root"

registry = ToolRegistry()

fileManager = FileManager(
    # tools=[
    #     "new_file",
    #     "read_file",
    #     "delete_file",
    #     "create_directory",
    #     "get_file_info",
    #     "directory_tree",
    # ],
)

gitManager = GitManager(
    # tools=[
    #     "git_status",
    #     "git_current_branch",
    #     "git_log",
    #     "git_diff",
    #     "git_staged_diff",
    #     "git_show",
    #     "git_add",
    #     "git_commit",
    #     "git_restore",
    # ],
)

searchManager = SearchManager(
    # tools=[
    #     "search_text",
    #     "search_regex",
    #     "search_text_ignore_case",
    #     "search_regex_ignore_case",
    #     "find_files",
    #     "search_file_names",
    #     "list_files",
    #     "search_by_extension",
    #     "search_text_in_files",
    #     "files_with_matches",
    #     "files_without_matches",
    #     "count_matches",
    # ],
)

registry.register(
    fileManager,
    gitManager,
    searchManager,
)
