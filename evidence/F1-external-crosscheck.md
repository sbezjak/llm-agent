# External cross-check of F1: the production metric catches it only after four knobs

> **TL;DR** - pointing DeepEval's `ToolCorrectnessMetric` (a widely-used,
> pytest-native agent-eval library) at the F1 finding shows the production metric is
> NOT blunt, but it catches F1 only after four separate authoring decisions, while
> our `args_grounded_in_prior_observations` checker catches it with none. The honest
> line is "as good as the reference AND threshold you write for it", not "the standard
> tool is blind".

Date: 2026-07-15. deepeval 4.1.0, offline (no model - `ToolCorrectnessMetric`'s score
is algorithmic). Test: `tests/external/test_deepeval_crosscheck.py`. Report:
`reports/report-external-crosscheck-probe-a-2026-07-15.html`. The finding under test is
F1 (`evidence/F1-ablation-schema-example.md`): the agent emits the dependent
`get_weather` call in the first reply with `city` guessed from the schema example
instead of read from the file.

## Why an external cross-check

The two sibling projects each triangulated their own hand-built detectors against a
recognized external tool (red team -> garak, RAG -> Ragas). This is the agent project's
version. Agent eval has no single standard the way garak owns red-team scanning; the
production landscape splits into cloud tracing+eval platforms (LangSmith, Braintrust,
Arize Phoenix, Langfuse, W&B Weave - off-machine) and pytest/CI-native trace-metric
libraries you point at your own frozen trace (DeepEval, Ragas). DeepEval fits this
project's offline, in-repo posture: pytest-native, and `ToolCorrectnessMetric` is
model-free, so it runs with nothing leaving the machine.

## The frozen trace

The F1 behaviour as a fixed trace (reconstructed from the ablation, no live run so both
detectors score identical input): `read_file` returns `Sydney`, but the dependent
`get_weather` guesses `city="Ljubljana"` from the schema example. The expected
trajectory a reviewer would hand-author carries the RIGHT city, `city="Sydney"`.

## The ladder

| rung | `ToolCorrectnessMetric` setting | score | `is_successful` |
|---|---|---|---|
| a | name-only default | 1.0 | PASS - misses F1 (the right tools were called) |
| b | `+ should_consider_ordering` | 1.0 | PASS - still misses (the tools are in a plausible order) |
| c | `+ INPUT_PARAMETERS`, default threshold 0.5 | 0.5 | PASS - DETECTS the wrong city (score halves) but 0.5 >= 0.5 waves it through |
| d | `+ INPUT_PARAMETERS + threshold=1.0` / `strict_mode` | 0.5 / 0 | FAIL - finally catches F1 |

Catching F1 with the production metric takes four authoring decisions: (1) hand-author
an expected-trajectory reference, (2) fill in the correct `city="Sydney"`, (3) opt into
input-parameter comparison, and (4) tighten the threshold off its permissive 0.5
default. Our `args_grounded_in_prior_observations` checker catches the same trace with
none of them - it derives "was this argument grounded in a prior observation" directly
from the trace, so it needs no per-task reference and no threshold tuning.

Rung (c) is the most interesting: the metric is not blunt, it DOES detect the wrong
argument - but its DEFAULT threshold passes a half-right call. A reviewer reading only
green/red at defaults would not see F1.

## A second, quieter signal

DeepEval's own data types - `LLMTestCase(tools_called=..., expected_tools=...)` and
`ToolCall(name, input_parameters)` - are the same shape as this project's hand-rolled
`Trace` / `Step` (`tool`, `args`, `observation`). The adapter that bridges them is a
few lines. Independent convergence on the production library's data model is a sign the
seams were built along the grain of the field, separate from the ladder result itself.

## Wiring notes (deepeval 4.1.0)

- Set `DEEPEVAL_TELEMETRY_OPT_OUT=1` - deepeval ships a Sentry + Confident-AI telemetry
  client; the env var keeps the cross-check fully offline.
- "Model-free" is only half true. The score is algorithmic, but the 4.1.0 constructor
  eagerly initialises a model and defaults to an OpenAI GPTModel (raises without an API
  key) even with `include_reason=False`. A never-called `DeepEvalBaseLLM` stub
  satisfies the constructor and keeps the probe offline and deterministic.
