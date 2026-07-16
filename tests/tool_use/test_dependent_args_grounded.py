"""A dependent tool argument must be grounded in a prior observation.

The task has a hard sequential dependency: the weather city is only knowable
after reading the file. The contract asserted here is that every get_weather
call uses a city that appeared in an earlier observation. The ablation
(evidence/F1-ablation-schema-example.md) showed the current SUT breaks this
9/9: it emits get_weather in the same first reply as read_file and fills the
city from the tool-schema example text instead. The oracle lives in
llm_agent/checkers/ (every call checked, not just the first - the
current SUT fails on the first either way)."""

import pytest

from llm_agent.checkers import args_grounded_in_prior_observations
from llm_agent.dataset import get_task
from llm_agent.runners import run_task

TASK = get_task("multi-tool-dependency")["task"]


@pytest.mark.live
@pytest.mark.xfail(
    strict=True,
    reason=(
        "qwen2.5:7b emits the dependent get_weather call in the same first reply as "
        "read_file and guesses the city verbatim from the schema example (ablation: "
        "9/9 premature, 6/6 example-verbatim, 0/9 recovered - F1 in reports/findings.json, "
        "raw traces in evidence/F1-ablation-schema-example.md). If this XPASSes the model "
        "started grounding dependent arguments - re-run the ablation and update F1."
    ),
)
async def test_dependent_arg_grounded_in_prior_observation():
    trace = await run_task(TASK)
    assert any(s.tool == "get_weather" for s in trace.steps), "agent never called get_weather"
    grounded = args_grounded_in_prior_observations(trace, "get_weather", "city")
    assert grounded.passed, grounded.reason
