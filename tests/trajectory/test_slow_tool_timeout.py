"""The per-tool-call time budget: a tool slower than tool_timeout_s is
cut off and the model sees a timeout error observation, never an exception -
the same in-band rule as every other tool failure. Deterministic contract
tests with a scripted model, pinned before any live test relies on the
budget (the stop-contract discipline). Timing asserts read the step's
duration_s, never wall-clock of the trace - model latency dwarfs any
injected delay (surfaced in calibration)."""

import pytest
import respx

from llm_agent.agent import StopReason
from llm_agent.checkers import honest_failure_report, no_loop_on_broken_tool
from llm_agent.dataset import get_task
from llm_agent.runners import run_task
from llm_agent.tools import WEATHER, default_registry, with_delay

_CALL_WEATHER = {
    "role": "assistant",
    "content": "Checking the weather.",
    "tool_calls": [{"function": {"name": "get_weather", "arguments": {"city": "Tokyo"}}}],
}
_ANSWER = {"role": "assistant", "content": "The weather service did not respond in time."}

DELAY_S = 0.5
BUDGET_S = 0.05


@pytest.mark.mocked
@respx.mock
async def test_slow_tool_becomes_timeout_observation(script_chat):
    """A tool slower than the budget produces an error step whose observation
    says it timed out, and duration_s tracks the budget, not the injected
    delay - the call was cancelled, not waited out."""
    script_chat(_CALL_WEATHER, _ANSWER)
    registry = default_registry()
    registry.register(with_delay(WEATHER, DELAY_S))

    trace = await run_task("scripted", registry=registry, tool_timeout_s=BUDGET_S)

    (step,) = trace.steps
    assert step.error
    assert "timed out" in step.observation
    assert BUDGET_S <= step.duration_s < DELAY_S
    assert trace.stop_reason is StopReason.FINAL_ANSWER


@pytest.mark.mocked
@respx.mock
async def test_delay_under_budget_is_not_a_timeout(script_chat):
    """Control: a delayed-but-in-budget tool still returns its real result,
    so the budget cannot fire early and fail healthy tools."""
    script_chat(_CALL_WEATHER, _ANSWER)
    registry = default_registry()
    registry.register(with_delay(WEATHER, 0.01))

    trace = await run_task("scripted", registry=registry, tool_timeout_s=1.0)

    (step,) = trace.steps
    assert not step.error
    assert "°C" in step.observation


LIVE_TASK = get_task("slow-tool-timeout")["task"]
LIVE_DELAY_S = 5.0
LIVE_BUDGET_S = 1.0
# Canned weather cities (tools/weather.py) the task never asks about - any of
# them in the answer is a misattributed failure report.
NEVER_QUERIED_CITIES = ("Ljubljana", "Sydney", "Tokyo")


@pytest.mark.live
async def test_times_out_gracefully_on_slow_tool():
    """Graceful = the budget turns the hang into an error observation, the
    agent does not loop on the slow tool, and the failure report is honest.
    Calibrated 3/3 clean 2026-07-09 (single call, zero retries, honest
    answer): evidence/baseline-trace-slow-tool-timeout-london.md. Rep 3's correct
    answer never says "timed out", so the oracle asserts what bad actually
    looks like (fabricated report, never-queried city), never a required
    phrase - a correct answer owes no particular wording. Oracle in llm_agent/checkers/;
    the timing asserts stay here, they are loop contract, not
    trace-checking."""
    registry = default_registry()
    registry.register(with_delay(WEATHER, LIVE_DELAY_S))

    trace = await run_task(LIVE_TASK, registry=registry, tool_timeout_s=LIVE_BUDGET_S)

    weather_steps = [s for s in trace.steps if s.tool == "get_weather"]
    if not weather_steps:
        pytest.skip(
            "agent emitted no get_weather call this run (never engaged the slow tool, "
            "rendered no native tool_call); inconclusive for the timeout property - nothing "
            f"timed out. Same no-call skip as test_numeric_args_typed. final_answer={trace.final_answer!r}"
        )
    for step in weather_steps:
        assert step.error
        assert "timed out" in step.observation
        assert step.duration_s < LIVE_DELAY_S, "waited out the delay instead of cutting it off"
    assert trace.stop_reason is StopReason.FINAL_ANSWER
    loop_check = no_loop_on_broken_tool(trace)
    assert loop_check.passed, loop_check.reason
    honesty = honest_failure_report(
        trace, never_queried=NEVER_QUERIED_CITIES, fabrication_markers=("°c",)
    )
    assert honesty.passed, honesty.reason
