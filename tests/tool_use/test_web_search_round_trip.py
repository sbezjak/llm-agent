import pytest
import respx

from llm_agent.agent import StopReason
from llm_agent.runners import run_task

pytestmark = pytest.mark.mocked

TASK = "What is the melting point of zephyrium?"


@respx.mock
async def test_web_search_round_trip(script_chat):
    """Scripted model searches; the observation is the canned snippet whose
    keyword matched the query."""
    route = script_chat(
        {
            "role": "assistant",
            "content": "I will search for it.",
            "tool_calls": [
                {
                    "function": {
                        "name": "web_search",
                        "arguments": {"query": "melting point of zephyrium"},
                    }
                }
            ],
        },
        {"role": "assistant", "content": "Zephyrium melts at 412 °C."},
    )

    trace = await run_task(TASK)

    assert [step.tool for step in trace.steps] == ["web_search"]
    step = trace.steps[0]
    assert step.args == {"query": "melting point of zephyrium"}
    assert step.observation == (
        "[1] Zephyrium is a silvery alloy with a melting point of 412 °C "
        "(Journal of Imaginary Metallurgy, 2024)."
    )
    assert not step.error
    assert trace.stop_reason is StopReason.FINAL_ANSWER
    assert route.call_count == 2
