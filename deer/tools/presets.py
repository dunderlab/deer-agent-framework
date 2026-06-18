from deer.tools.builtin import (
    FileManager,
    GitManager,
    SearchManager,
    MemoryManager,
    NetworkManager,
    RuntimeManager,
    StructuredDataInspector,
    SystemInspector,
    PythonEditor,
    JSONEditor,
    XMLEditor,
    YAMLEditor,
    TOMLEditor,
)


class Preset:

    CODE_REPAIR = {
        FileManager,
        GitManager,
        SearchManager,
        RuntimeManager,
        MemoryManager,
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
        MemoryManager,
    }

    SYSTEM_ADMIN = {
        SystemInspector,
        RuntimeManager,
        FileManager,
        MemoryManager,
    }

    WEB_AUTONOMOUS = {
        NetworkManager,
        FileManager,
        SearchManager,
        MemoryManager,
    }

    ALL_TOOLS = {
        FileManager,
        GitManager,
        SearchManager,
        MemoryManager,
        NetworkManager,
        RuntimeManager,
        StructuredDataInspector,
        SystemInspector,
    }
