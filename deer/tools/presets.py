from deer.tools.builtin import (
    FileManager,
    GitManager,
    SearchManager,
    HTTPClient,
    RuntimeManager,
    StructuredDataInspector,
    SystemInspector,
    PythonEditor,
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
        SearchManager,
        RuntimeManager,
    }

    CODE_EDITOR = {
        PythonEditor,
        JSONEditor,
        XMLEditor,
        YAMLEditor,
        TOMLEditor,
    }

    DATA_ANALYST = {
        StructuredDataInspector,
        FileManager,
        SearchManager,
    }

    SYSTEM_ADMIN = {
        SystemInspector,
        RuntimeManager,
        FileManager,
        SearchManager,
    }

    WEB_AUTONOMOUS = {
        HTTPClient,
        FileManager,
        SearchManager,
    }

    ALL_TOOLS = {
        FileManager,
        GitManager,
        SearchManager,
        HTTPClient,
        RuntimeManager,
        StructuredDataInspector,
        SystemInspector,
        PythonEditor,
        JSONEditor,
        XMLEditor,
        YAMLEditor,
        TOMLEditor,
        LogicProvider,
    }
