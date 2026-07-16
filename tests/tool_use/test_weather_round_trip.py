import pytest
import respx

from llm_agent.agent import StopReason
from llm_agent.runners import run_task

pytestmark = pytest.mark.mocked

TASK = "What is the weather in Ljubljana right now?"


@respx.mock
async def test_weather_round_trip(script_chat):
    """Scripted model calls the weather mock; the observation is the default
    canned report (city lookup is case-insensitive)."""
    route = script_chat(
        {
            "role": "assistant",
            "content": "I will check the weather.",
            "tool_calls": [
                {"function": {"name": "get_weather", "arguments": {"city": "Ljubljana"}}}
            ],
        },
        {"role": "assistant", "content": "Ljubljana is clear at 28 °C."},
    )

    trace = await run_task(TASK)

    assert [step.tool for step in trace.steps] == ["get_weather"]
    step = trace.steps[0]
    assert step.args == {"city": "Ljubljana"}
    assert step.observation == "Clear, 28 °C, wind 5 km/h from the northwest."
    assert not step.error
    assert trace.stop_reason is StopReason.FINAL_ANSWER
    assert route.call_count == 2
