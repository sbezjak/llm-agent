"""write_file round trip (mocked): the observation confirms the write AND
the file's end state on disk matches - the first tool where the assert
target is the world, not the observation. The escape test guards the only
thing keeping tests from writing outside their tmp sandbox."""

import pytest
import respx

from llm_agent.agent import StopReason
from llm_agent.runners import run_task
from llm_agent.tools import ToolRegistry, write_file_tool

pytestmark = pytest.mark.mocked

_ANSWER = {"role": "assistant", "content": "Done, the file is written."}


def _call_write(path: str) -> dict:
    return {
        "role": "assistant",
        "content": "I will write the file.",
        "tool_calls": [
            {"function": {"name": "write_file", "arguments": {"path": path, "content": "hello"}}}
        ],
    }


@respx.mock
async def test_write_file_round_trip(script_chat, tmp_path):
    script_chat(_call_write("note.txt"), _ANSWER)

    trace = await run_task("scripted", registry=ToolRegistry([write_file_tool(tmp_path)]))

    (step,) = trace.steps
    assert not step.error
    assert step.observation == "wrote 5 characters to note.txt"
    assert (tmp_path / "note.txt").read_text() == "hello"
    assert trace.stop_reason is StopReason.FINAL_ANSWER


@respx.mock
async def test_write_file_escape_is_error_not_write(script_chat, tmp_path):
    """A path that resolves outside the sandbox becomes an error observation
    and nothing is written anywhere (the excessive-agency surface)."""
    script_chat(_call_write("../escaped.txt"), _ANSWER)

    trace = await run_task("scripted", registry=ToolRegistry([write_file_tool(tmp_path)]))

    (step,) = trace.steps
    assert step.error
    assert "escapes" in step.observation
    assert not (tmp_path.parent / "escaped.txt").exists()
