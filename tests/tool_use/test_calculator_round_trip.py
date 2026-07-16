import pytest
import respx

from llm_agent.agent import StopReason
from llm_agent.runners import run_task

pytestmark = pytest.mark.mocked

TASK = "What is 17 * 23?"


@respx.mock
async def test_calculator_round_trip_stops_on_sentinel(script_chat):
    """One task end to end: the scripted model asks for the calculator, gets
    the observation back, then answers without tool calls (the sentinel).
    Asserts over the trace, not just the final answer."""
    route = script_chat(
        {
            "role": "assistant",
            "content": "I will multiply with the calculator.",
            "tool_calls": [
                {
                    "function": {
                        "name": "calculator",
                        "arguments": {"expression": "17 * 23"},
                    }
                }
            ],
        },
        {"role": "assistant", "content": "17 * 23 = 391."},
    )

    trace = await run_task(TASK)

    assert [step.tool for step in trace.steps] == ["calculator"]  # right tool, exactly once
    step = trace.steps[0]
    assert step.args == {"expression": "17 * 23"}  # right args, verbatim
    assert step.observation == "391"  # real tool executed, not a canned string
    assert not step.error
    assert step.thought == "I will multiply with the calculator."
    assert trace.stop_reason is StopReason.FINAL_ANSWER  # stopped on the sentinel, not the cap
    assert trace.final_answer == "17 * 23 = 391."
    assert route.call_count == 2  # two model calls total, no over-calling
