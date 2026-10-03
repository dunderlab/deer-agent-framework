from deer.tools.providers import (
    FileManager,
    GitManager,
    CodeSearcher,
    HTTPClient,
    DevCommandRunner,
    SysAdminRunner,
    ProcessManager,
    SQLiteManager,
    CSVManager,
    SystemObserver,
    PythonStructEditor,
    DependencyAnalyzer,
    JSONEditor,
    XMLEditor,
    YAMLEditor,
    TOMLEditor,
    LogicProvider,
)


class Preset:

    # For diagnosing, fixing, and verifying bugs in existing code.
    CODE_REPAIR = {
        FileManager,
        GitManager,
        CodeSearcher,
        DevCommandRunner,
        ProcessManager,
        PythonStructEditor,
        DependencyAnalyzer,
    }

    # For structural changes to source code and project configurations.
    CODE_EDITOR = {
        PythonStructEditor,
        DependencyAnalyzer,
        JSONEditor,
        XMLEditor,
        YAMLEditor,
        TOMLEditor,
        DevCommandRunner,
        GitManager,
    }

    # For analyzing and extracting insights from structured datasets.
    DATA_ANALYST = {
        SQLiteManager,
        CSVManager,
        FileManager,
        CodeSearcher,
        LogicProvider,
    }

    # For monitoring and managing system health and background processes.
    SYSTEM_ADMIN = {
        SystemObserver,
        SysAdminRunner,
        ProcessManager,
        FileManager,
        CodeSearcher,
    }

    # For interacting with remote endpoints and processing network data.
    NETWORK_OPERATOR = {
        HTTPClient,
        FileManager,
        CodeSearcher,
        JSONEditor,
        CSVManager,
    }

    # For surgical structural improvements and impact analysis.
    REFACTORING_EXPERT = {
        PythonStructEditor,
        DependencyAnalyzer,
        CodeSearcher,
        GitManager,
        FileManager,
    }

    # For safely modifying configuration files without touching source code.
    CONFIG_SPECIALIST = {
        JSONEditor,
        XMLEditor,
        YAMLEditor,
        TOMLEditor,
        FileManager,
    }

    ALL_TOOLS = {
        FileManager,
        GitManager,
        CodeSearcher,
        HTTPClient,
        DevCommandRunner,
        SysAdminRunner,
        ProcessManager,
        SQLiteManager,
        CSVManager,
        SystemObserver,
        PythonStructEditor,
        DependencyAnalyzer,
        JSONEditor,
        XMLEditor,
        YAMLEditor,
        TOMLEditor,
        LogicProvider,
    }
