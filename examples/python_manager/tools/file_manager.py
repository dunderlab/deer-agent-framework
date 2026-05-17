from deer.tools.decorators import tool
from deer.schema.io import Struct


class FileManager:
    """Tools for managing files."""

    #
    # @tool(
    #     name="new_file",
    #     description="Creates a new file with the given content.",
    # )
    # def new_file(
    #     params: Struct(
    #         path=str,
    #         content=str,
    #     ),
    # ) -> Struct(status=str):
    #
    #     with open(params["path"], "w") as f:
    #         f.write(params["content"])
    #
    #     return {"status": "success"}
