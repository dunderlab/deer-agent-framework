from deer.tools.registry import ToolRegistry
from deer.tools.builtin import (
    FileManager,
    GitManager,
    SearchManager,
    MemoryManager,
    NetworkManager,
    RuntimeManager,
    StructuredDataInspector,
    SystemInspector,
)

jail_path = "/Users/yeison/Development/deer-agent-framework/sandbox/root"

tool_registry = ToolRegistry()

fileManager = FileManager(
    # tools=[
    #     "new_file",
    #     "read_file",
    #     "delete_file",
    #     "create_directory",
    #     "get_file_info",
    #     "directory_tree",
    #     "patch_file",
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

memoryManager = MemoryManager(
    # tools=[
    #     "store_key_insight",
    #     "retrieve_key_insight",
    #     "list_memory_keys",
    #     "clear_context_memory",
    # ]
)

networkManager = NetworkManager(
    # tools=[
    #     "fetch_endpoint",
    #     "download_asset",
    #     "check_url_availability",
    # ]
)

runtimeManager = RuntimeManager(
    # tools=[
    #     "execute_test_suite",
    #     "compile_source_code",
    #     "check_process_status",
    #     "terminate_process",
    # ]
)

structuredDataInspector = StructuredDataInspector(
    # tools=[
    #     "inspect_json_keys",
    #     "preview_csv_columns",
    #     "query_sqlite_metadata",
    #     "execute_sqlite_statement",
    # ]
)

systemInspector = SystemInspector(
    # tools=[
    #     "get_environment_variable",
    #     "list_active_processes",
    #     "check_network_sockets",
    # ]
)

tool_registry.register(
    fileManager,
    gitManager,
    searchManager,
    memoryManager,
    networkManager,
    runtimeManager,
    structuredDataInspector,
    systemInspector,
)
