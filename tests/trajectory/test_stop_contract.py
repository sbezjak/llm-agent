"""The loop's two stop conditions, pinned with a scripted model.

"Stopped because done" (sentinel: a reply with zero tool calls) vs "stopped
because it hit the cap" (max_steps model calls) is the distinction every
stop-vs-loop test draws - so the contract itself gets deterministic tests
before any live test relies on it. The task strings are irrelevant here: the
model is scripted, only the loop is under test."""

import pytest
import respx

from llm_agent.agent import StopReason
from llm_agent.runners import run_task

pytestmark = pytest.mark.mocked

_CALL_WEATHER = {
    "role": "assistant",
    "content": "Checking the weather again.",
    "tool_calls": [{"function": {"name": "get_weather", "arguments": {"city": "Tokyo"}}}],
}
_ANSWER = {"role": "assistant", "content": "The answer is 42."}


@respx.mock
async def test_cap_stops_a_looping_model(script_chat):
    """A model that never stops calling tools gets cut off at max_steps model
    calls: MAX_STEPS, no final answer. The script holds an answer at position
    4 that the loop must never request - call_count proves the cap bit, not
    script exhaustion."""
    route = script_chat(_CALL_WEATHER, _CALL_WEATHER, _CALL_WEATHER, _ANSWER)

    trace = await run_task("scripted", max_steps=3)

    assert trace.stop_reason is StopReason.MAX_STEPS
    assert trace.final_answer is None
    assert [step.tool for step in trace.steps] == ["get_weather"] * 3
    assert route.call_count == 3


@respx.mock
async def test_sentinel_wins_when_cap_would_also_apply(script_chat):
    """An immediate no-tool-call reply is FINAL_ANSWER even at max_steps=1 -
    the sentinel is checked before the cap can bite, so a clean done never
    gets misreported as a cutoff."""
    script_chat(_ANSWER)

    trace = await run_task("scripted", max_steps=1)

    assert trace.stop_reason is StopReason.FINAL_ANSWER
    assert trace.final_answer == "The answer is 42."
    assert trace.steps == ()
