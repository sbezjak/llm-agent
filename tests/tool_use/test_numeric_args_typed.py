"""Numeric tool arguments must arrive with the schema's declared type.

The probe is a test-local add(a: number, b: number) tool, the only tool in
the registry - the shipped calculator takes a string expression, so string
args cannot violate its schema. Model under test is llama3.2 (the optional
second model, not the SUT baseline qwen2.5); the provider override keeps
the SUT seam untouched.

Probed 2026-07-08 (3 reps each, evidence/F2-string-args-float.md): int
args arrive typed 3/3, float args arrive as STRINGS 3/3. Downstream of the
strings, the deliberately unvalidated dispatch concatenates
'15.5' + '7.25' into '15.57.25' with error=False - a silent garbage result -
and the model then masks it by computing 22.75 in-model. Outcome correct,
tool chain silently broken: F2 in reports/findings.json."""

import logging

import pytest

from llm_agent.agent import Trace
from llm_agent.dataset import get_task
from llm_agent.providers.ollama import OllamaProvider
from llm_agent.runners import run_task
from llm_agent.tools import Tool, ToolRegistry

pytestmark = pytest.mark.live

MODEL = "llama3.2:latest"

log = logging.getLogger(__name__)
INT_REPS = 8  # arg typing is stochastic; measure a rate over reps, never assert one draw


def add_tool() -> Tool:
    async def add(a, b):
        return str(a + b)

    return Tool(
        name="add",
        description="Add two numbers and return the sum.",
        parameters={
            "type": "object",
            "properties": {
                "a": {"type": "number", "description": "First addend"},
                "b": {"type": "number", "description": "Second addend"},
            },
            "required": ["a", "b"],
        },
        handler=add,
    )


async def _run(task_id: str) -> Trace:
    return await run_task(
        get_task(task_id)["task"],
        provider=OllamaProvider(model=MODEL, timeout=300.0),
        registry=ToolRegistry([add_tool()]),
    )


def _add_args_or_skip(trace: Trace) -> dict:
    """The arg TYPES are only observable if the model actually emitted an add
    tool call. llama3.2's native tool-calling is flaky: it can render the call as
    a JSON string in the content field instead of a structured tool_call, so the
    loop sees no tool call, stops on the sentinel, and steps==0. That run is
    INCONCLUSIVE for arg typing, not a failure of it - skip rather than let the
    'agent never called add' assertion conflate a no-call flake with a type bug."""
    add_steps = [step for step in trace.steps if step.tool == "add"]
    if not add_steps:
        pytest.skip(
            "llama3.2 emitted no add tool call this run (rendered it as text "
            "content, not a native tool_call); inconclusive for arg typing. "
            f"final_answer={trace.final_answer!r}"
        )
    return add_steps[0].args


async def test_int_args_arrive_typed():
    """The control, as a RATE not a single draw. Integer args respect the number
    schema the large majority of the time (isolated calibration 7/7 typed when
    called, 2026-07-15), UNLIKE floats which stringify (F2). The point is the
    type-DEPENDENT contrast: ints can arrive typed, floats never do (the strict
    xfail below proves the float side).

    Why a rate and not a single assert: the original one-draw assert flaked twice
    in full-suite runs (both string - the stochastic tail of an ~85% property),
    the same single-draw-of-a-stochastic-property landmine as F8. So we sample:
    run INT_REPS times, drop no-call reps as inconclusive (llama3.2's native
    tool-calling is itself flaky), log the full typed/string rate for reading, and
    gate on the durable invariant - ints arrive typed at least sometimes. That
    fails loudly only if ints start stringifying like floats (F2 drift), while
    tolerating the normal wobble a single assert could not."""
    typed = strings = 0
    details = []
    for _ in range(INT_REPS):
        add_steps = [s for s in (await _run("numeric-args-int")).steps if s.tool == "add"]
        if not add_steps:
            continue  # no native add call: inconclusive for arg typing, not a data point
        args = add_steps[0].args
        ok = all(isinstance(v, int | float) for v in args.values())
        typed += ok
        strings += not ok
        details.append(f"{args} typed={ok}")
    conclusive = typed + strings
    log.info(
        "INT-ARGS TYPING RATE: typed=%d string=%d of %d conclusive / %d reps | %s",
        typed,
        strings,
        conclusive,
        INT_REPS,
        "; ".join(details) or "(all no-call)",
    )
    if conclusive < 2:
        pytest.skip(f"only {conclusive} conclusive reps (llama3.2 no-call flake); inconclusive")
    assert typed >= 1, (
        f"int args typed 0/{conclusive} conclusive reps - ints now stringify like floats, "
        "the type-dependent contrast (F2) no longer holds; re-probe F2"
    )


@pytest.mark.xfail(
    strict=True,
    reason=(
        "llama3.2 sends float args as strings despite the number schema (3/3 on "
        "2026-07-08, vs int args typed 3/3 - F2 in reports/findings.json, raw traces "
        "in evidence/F2-string-args-float.md). If this XPASSes the model or Ollama "
        "started coercing float types - re-probe and update F2."
    ),
)
async def test_float_args_arrive_typed():
    args = _add_args_or_skip(await _run("numeric-args-float"))
    assert all(isinstance(v, int | float) for v in args.values()), args
