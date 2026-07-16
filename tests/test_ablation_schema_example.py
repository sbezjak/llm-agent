"""Ablation experiment (F1): is the tool-schema example
the source of the guessed argument in the premature get_weather call?

Calibration observed the multi-tool task emit read_file AND get_weather in the first
reply, with get_weather's city guessed as 'Ljubljana' - verbatim the schema
example. One observation is circumstantial. Here the same task reruns under
three conditions that differ ONLY in the schema example for get_weather's
city parameter (baseline 'Ljubljana', sentinel 'Casablanca', no example).
If the guess follows the example, doc-example leakage is the mechanism.

This is an experiment, not a regression test: it asserts only the structural
trace contract; the evidence is the full traces in the report/log, plus the
one-line ABLATION summary logged per run. The sentinel is a real city that
appears nowhere except the schema (not in the task, not in cities.txt), so
a sentinel guess can only have come from the schema text. The canned
conditions dict is identical in all three conditions (defaults + sentinel),
so post-observation behavior is comparable too.
"""

import copy
import dataclasses
import logging

import pytest

from llm_agent.agent import StopReason, Trace
from llm_agent.runners import run_task
from llm_agent.tools import ToolRegistry, default_registry
from llm_agent.tools.weather import _DEFAULT_CONDITIONS, weather_tool

log = logging.getLogger(__name__)

pytestmark = pytest.mark.live

TASK = "Read the file cities.txt, then tell me the current weather in the city it names."

CONDITIONS = {
    "baseline-ljubljana": "City name, e.g. 'Ljubljana'",
    "sentinel-casablanca": "City name, e.g. 'Casablanca'",
    "no-example": "City name",
}

REPORTS = {**_DEFAULT_CONDITIONS, "casablanca": "Sunny, 31 °C, wind 10 km/h from the west."}


def _registry(city_description: str) -> ToolRegistry:
    weather = weather_tool(conditions=REPORTS)
    parameters = copy.deepcopy(weather.parameters)
    parameters["properties"]["city"]["description"] = city_description
    registry = default_registry()
    registry.register(dataclasses.replace(weather, parameters=parameters))
    return registry


def _assert_well_formed(trace: Trace) -> None:
    if trace.stop_reason is StopReason.FINAL_ANSWER:
        assert trace.final_answer
    else:
        assert trace.stop_reason is StopReason.MAX_STEPS
        assert trace.final_answer is None


@pytest.mark.parametrize("rep", [1, 2, 3])
@pytest.mark.parametrize("condition", sorted(CONDITIONS))
async def test_multi_tool_task_ablation(condition: str, rep: int):
    trace = await run_task(TASK, registry=_registry(CONDITIONS[condition]))
    weather_calls = [(s.index, s.args.get("city")) for s in trace.steps if s.tool == "get_weather"]
    log.info(
        "ABLATION condition=%s rep=%d get_weather_calls=%s stop=%s final=%r",
        condition,
        rep,
        weather_calls,
        trace.stop_reason.value,
        trace.final_answer,
    )
    _assert_well_formed(trace)
