"""Probe A of the DeepEval external cross-check (model-free, deterministic).

Triangulates our hand-built grounding detector against a production agent-eval
library on ONE frozen trace - the F1 finding (get_weather emitted in the first
reply with `city` guessed from the schema example instead of read from the file;
ablation 9/9, evidence/F1-ablation-schema-example.md). No live agent run: the
trace is reconstructed from the ablation so both detectors score identical input.

The finding is the ladder, not a faceplant. DeepEval's ToolCorrectnessMetric is
not blunt - but it catches F1 only after FOUR authoring decisions, while
args_grounded_in_prior_observations catches it with none:

    rung  setting                                     score  is_successful
    (a)   name-only default                           1.0    PASS  (misses F1)
    (b)   + should_consider_ordering                  1.0    PASS  (still misses)
    (c)   + INPUT_PARAMETERS, default threshold 0.5   0.5    PASS  (detects, waved through)
    (d)   + INPUT_PARAMETERS + threshold 1.0 / strict 0.5/0  FAIL  (catches F1)

So the production metric is "as good as the reference AND the threshold you write
for it"; our checker encodes the grounding property directly. Both true, both in
the article paragraph. Deterministic + offline (NullModel, include_reason=False),
so this is a plain assertion, not a calibration.
"""

import pytest
from deepeval.metrics import ToolCorrectnessMetric
from deepeval.test_case import ToolCall, ToolCallParams

from llm_agent.agent import Step, StopReason, Trace
from llm_agent.checkers import args_grounded_in_prior_observations

from .deepeval_adapter import NullModel, trace_to_testcase

pytestmark = pytest.mark.external


def _f1_trace() -> Trace:
    """The F1 behaviour as a frozen Trace: read_file returns 'Sydney', but the
    dependent get_weather (same first reply) guesses 'Ljubljana' from the schema
    example - the guessed city appears in no observation. Faithful to the ablation
    baseline rep (evidence/F1-ablation-schema-example.md)."""
    return Trace(
        task="Read the file cities.txt, then tell me the current weather in the city it names.",
        steps=(
            Step(0, "", "read_file", {"path": "cities.txt"}, "Sydney", False, 0.01),
            Step(
                1, "", "get_weather", {"city": "Ljubljana"}, "It is 20C in Ljubljana.", False, 0.01
            ),
        ),
        final_answer="It is currently 20C in Ljubljana.",
        stop_reason=StopReason.FINAL_ANSWER,
    )


# The hand-authored reference trajectory DeepEval needs: the RIGHT city, read from
# the file. Authoring this by hand (name + expected arg) is exactly the cost the
# probe measures.
_EXPECTED = [
    ToolCall(name="read_file", input_parameters={"path": "cities.txt"}),
    ToolCall(name="get_weather", input_parameters={"city": "Sydney"}),
]


def _rung(testcase, **kwargs) -> tuple[float, bool]:
    metric = ToolCorrectnessMetric(model=NullModel(), include_reason=False, **kwargs)
    metric.measure(testcase)
    return metric.score, metric.is_successful()


def test_our_grounding_checker_catches_f1():
    """The detector we trust: the guessed city is in no prior observation, so
    args_grounded_in_prior_observations fails - no reference, no threshold tuning."""
    result = args_grounded_in_prior_observations(_f1_trace(), "get_weather", "city")
    assert result.passed is False
    assert "Ljubljana" in result.reason


def test_deepeval_ladder_catches_f1_only_at_the_top_rung():
    """DeepEval's ToolCorrectnessMetric across the four rungs - the honest ladder."""
    tc = trace_to_testcase(_f1_trace(), expected_tools=_EXPECTED)

    # (a) name-only default: right tools were called, so it passes and misses F1.
    score_a, pass_a = _rung(tc)
    assert (score_a, pass_a) == (1.0, True)

    # (b) + ordering: the tools are in a plausible order too, so still a pass.
    score_b, pass_b = _rung(tc, should_consider_ordering=True)
    assert (score_b, pass_b) == (1.0, True)

    # (c) + input-parameter comparison, default threshold 0.5: NOW it detects the
    # wrong city (score halves) - but 0.5 >= 0.5, so is_successful is still True.
    score_c, pass_c = _rung(tc, evaluation_params=[ToolCallParams.INPUT_PARAMETERS])
    assert score_c == 0.5 and pass_c is True

    # (d) same, but threshold tightened off its permissive default: finally fails.
    score_d, pass_d = _rung(tc, evaluation_params=[ToolCallParams.INPUT_PARAMETERS], threshold=1.0)
    assert pass_d is False and score_d < 1.0
