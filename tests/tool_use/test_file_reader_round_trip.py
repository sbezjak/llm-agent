import pytest
import respx

from llm_agent.agent import StopReason
from llm_agent.runners import run_task

pytestmark = pytest.mark.mocked

TASK = "What does the file cities.txt contain?"


@respx.mock
async def test_file_reader_round_trip(script_chat):
    """Scripted model reads a real file from the data/ sandbox; the
    observation is the actual file content, not a canned string."""
    route = script_chat(
        {
            "role": "assistant",
            "content": "I will read the file.",
            "tool_calls": [
                {"function": {"name": "read_file", "arguments": {"path": "cities.txt"}}}
            ],
        },
        {"role": "assistant", "content": "The file names one city: Sydney."},
    )

    trace = await run_task(TASK)

    assert [step.tool for step in trace.steps] == ["read_file"]
    step = trace.steps[0]
    assert step.args == {"path": "cities.txt"}
    assert step.observation == "Sydney\n"  # read from data/cities.txt on disk
    assert not step.error
    assert trace.stop_reason is StopReason.FINAL_ANSWER
    assert route.call_count == 2
