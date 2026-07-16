from pathlib import Path

from .base import Tool


def write_file_tool(root: Path) -> Tool:
    """Sandboxed write tool - the project's only state-changing tool, added
    for the outcome dimension (end-state asserts) and the excessive-agency
    surface. root is required, never defaulted: a default rooted at data/
    would let a live agent overwrite its own task suite. Not part of
    default_registry - locked tests keep the 4-tool prompt context they were
    calibrated on; tests that assert an end state register it explicitly,
    rooted at a per-test tmp dir."""

    async def write_file(path: str, content: str) -> str:
        resolved = (root / path).resolve()
        # Same escape rule as read_file: writing outside the sandbox must
        # become an error observation the model sees, never a write.
        if not resolved.is_relative_to(root.resolve()):
            raise ValueError(f"path {path!r} escapes the {root}/ sandbox")
        resolved.write_text(content)
        return f"wrote {len(content)} characters to {path}"

    return Tool(
        name="write_file",
        description="Write text to a file in the data directory, creating or overwriting it.",
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "File path relative to the data directory, e.g. 'draft.txt'",
                },
                "content": {"type": "string", "description": "The text content to write."},
            },
            "required": ["path", "content"],
        },
        handler=write_file,
    )
