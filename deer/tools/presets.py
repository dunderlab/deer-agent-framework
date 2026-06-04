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


class Preset:

    CODE_REPAIR = {
        FileManager,
        GitManager,
        SearchManager,
        RuntimeManager,
        MemoryManager,
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
