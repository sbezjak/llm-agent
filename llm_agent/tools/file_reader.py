from pathlib import Path

from ..dataset import DATA_DIR
from .base import Tool


def file_reader_tool(root: Path = DATA_DIR) -> Tool:
    async def read_file(path: str) -> str:
        resolved = (root / path).resolve()
        # The sandbox is the excessive-agency surface: an escape attempt
        # must become an error observation the model sees, never a file read.
        if not resolved.is_relative_to(root.resolve()):
            raise ValueError(f"path {path!r} escapes the {root}/ sandbox")
        return resolved.read_text()

    return Tool(
        name="read_file",
        description="Read a text file from the data directory and return its contents.",
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "File path relative to the data directory, e.g. 'cities.txt'",
                }
            },
            "required": ["path"],
        },
        handler=read_file,
    )


FILE_READER = file_reader_tool()
