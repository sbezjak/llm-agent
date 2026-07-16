"""Adapter: our Trace -> a DeepEval LLMTestCase, plus a never-called model stub.

The external cross-check triangulates detectors we already trust against a
production agent-eval library (DeepEval). This module is the only real plumbing:
one function mapping our hand-rolled Trace to DeepEval's test-case shape, so the
same frozen trace can be scored by both our checkers and DeepEval's metrics.

Kept in tests/ (not the package) on purpose - deepeval is a dev-only cross-check
dependency and never touches the SUT.

Two wiring warts of deepeval 4.1.0 live here, both worth knowing:
  - Telemetry: deepeval ships a Sentry + Confident-AI client. Importing this
    module sets DEEPEVAL_TELEMETRY_OPT_OUT so the cross-check stays fully offline.
  - "Model-free" is only half true. ToolCorrectnessMetric's SCORE is algorithmic,
    but the 4.1.0 constructor eagerly initialises a model and defaults to an
    OpenAI GPTModel (raises DeepEvalError without an API key) even when
    include_reason=False. NullModel satisfies that constructor and refuses to be
    called, keeping the model-free probe genuinely offline and deterministic.
"""

import os

os.environ.setdefault("DEEPEVAL_TELEMETRY_OPT_OUT", "1")

from deepeval.models import DeepEvalBaseLLM  # noqa: E402
from deepeval.test_case import LLMTestCase, ToolCall  # noqa: E402

from llm_agent.agent import Trace


def trace_to_testcase(trace: Trace, expected_tools: list[ToolCall] | None = None) -> LLMTestCase:
    """Map a Trace to an LLMTestCase. Each Step becomes a ToolCall carrying its
    name and args (input_parameters) - exactly the fields ToolCorrectnessMetric
    reads. expected_tools is the hand-authored reference trajectory the metric
    needs; the whole point of Probe A is how much of it you must write by hand."""
    return LLMTestCase(
        input=trace.task,
        actual_output=trace.final_answer or "",
        tools_called=[
            ToolCall(name=step.tool, input_parameters=dict(step.args)) for step in trace.steps
        ],
        expected_tools=expected_tools,
    )


class NullModel(DeepEvalBaseLLM):
    """A model that refuses to run. Passed to ToolCorrectnessMetric so its
    eager-init constructor is satisfied without reaching for OpenAI; with
    include_reason=False it is never invoked, so the probe stays deterministic.
    Any call is a bug (the score path must not touch a model), so it asserts."""

    def load_model(self):
        return None

    def generate(self, *args, **kwargs):
        raise AssertionError("NullModel called - Probe A must stay model-free")

    async def a_generate(self, *args, **kwargs):
        raise AssertionError("NullModel called - Probe A must stay model-free")

    def get_model_name(self) -> str:
        return "null-stub"
