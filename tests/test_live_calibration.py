"""First live traces against the SUT model - calibration reading, not
assertions. Each test drives one fabricated task and logs the full trace;
the pytest-html report is the reading surface. Only the structural trace
contract is asserted; finding candidates are captured, tests that lock
them in come later.

The web-search and file tasks use fabricated facts (zephyrium, Veloria,
cities.txt), so an answer containing them proves the model grounded on the
tool, not on its own memory."""

import pytest

from llm_agent.agent import StopReason, Trace
from llm_agent.runners import run_task

pytestmark = pytest.mark.live


def _assert_well_formed(trace: Trace) -> None:
    if trace.stop_reason is StopReason.FINAL_ANSWER:
        assert trace.final_answer
    else:
        assert trace.stop_reason is StopReason.MAX_STEPS
        assert trace.final_answer is None


async def test_calculator_task():
    _assert_well_formed(await run_task("What is 17% of 3200, minus 44?"))


async def test_file_reader_task():
    _assert_well_formed(await run_task("What does the file cities.txt contain?"))


async def test_weather_task():
    _assert_well_formed(await run_task("What is the weather in Ljubljana right now?"))


async def test_web_search_task():
    _assert_well_formed(await run_task("What is the melting point of zephyrium?"))


async def test_multi_tool_task():
    _assert_well_formed(
        await run_task(
            "Read the file cities.txt, then tell me the current weather in the city it names."
        )
    )
