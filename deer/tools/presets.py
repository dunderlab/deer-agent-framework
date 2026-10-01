from deer.tools.builtin import (
    FileManager,
    GitManager,
    CodeSearcher,
    HTTPClient,
    CommandRunner,
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

    CODE_REPAIR = {
        FileManager,
        GitManager,
        CodeSearcher,
        CommandRunner,
        ProcessManager,
    }

    CODE_EDITOR = {
        PythonStructEditor,
        DependencyAnalyzer,
        JSONEditor,
        XMLEditor,
        YAMLEditor,
        TOMLEditor,
    }

    DATA_ANALYST = {
        SQLiteManager,
        CSVManager,
        FileManager,
        CodeSearcher,
    }

    SYSTEM_ADMIN = {
        SystemObserver,
        CommandRunner,
        ProcessManager,
        FileManager,
        CodeSearcher,
    }

    WEB_AUTONOMOUS = {
        HTTPClient,
        FileManager,
        CodeSearcher,
    }

    ALL_TOOLS = {
        FileManager,
        GitManager,
        CodeSearcher,
        HTTPClient,
        CommandRunner,
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
