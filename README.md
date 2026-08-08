# llm-agent

> Part of a [5-project AI/QA testing portfolio](https://github.com/sbezjak/sbezjak) - all projects and write-ups.

A pytest suite that tests a mini **ReAct** agent - a system that does not just
answer once but *plans, calls tools, and acts over several steps*. The tests
assert over the full **trace of tool calls**, not just the final answer, because
in an agent the bug is usually in the *chain*, not one reply.

The one lesson across every finding: **the final answer tells you nothing, only
the trace does.**

- **[Walkthrough](docs/walkthrough.md)** - the guided tour: every finding, how it
  works, what production would add. Start here.
- **[Findings dashboard](https://sbezjak.github.io/llm-agent/reports/findings-dashboard.html)** -
  all nine failure modes at a glance, each with its live failure-rate and captured trace.
- This README - the reference: what's here, how to run it.

## What it tests - the five dimensions

| Dimension | Question it asks | Where |
|---|---|---|
| **outcome** | did the world end up correct? | `tests/outcome/` |
| **trajectory** | did it take the right *steps*? | `tests/trajectory/` |
| **tool_use** | right tool, right args, right time? | `tests/tool_use/` |
| **multi_turn** | does an earlier poisoned turn get trusted later? | `tests/multi_turn/` |
| **excessive_agency** | OWASP LLM06 - does it do more than asked? | `tests/excessive_agency/` |

## The findings

Nine failure modes on `qwen2.5:7b` (F2 on `llama3.2`, F9 on `llama3.1:8b`), each
locked in by a test. Severity is the impact if it shipped as-is. Mechanisms and
traces: [walkthrough](docs/walkthrough.md), [dashboard](https://sbezjak.github.io/llm-agent/reports/findings-dashboard.html),
`evidence/`.

| # | Failure mode | Sev | Where |
|---|---|---|---|
| **F1** | Dependent tool argument guessed from the schema's own example | high | `tests/tool_use/test_dependent_args_grounded.py` |
| **F2** | Float args arrive as strings, silently concatenated | med | `tests/tool_use/test_numeric_args_typed.py` |
| **F3** | Phantom tool use - claims a web search it never ran | high | `tests/checkers/` · `TestNoPhantomToolClaims` |
| **F4** | Ungrounded synthesis under conflict - invents an average | med | `tests/checkers/` · `TestAnswerNumbersGrounded` |
| **F5** | Phantom compliance - narrates an injected write it never made | med | `tests/checkers/` · `TestNoPhantomActionClaims` |
| **F6** | Attacker-planted fact repeated as established policy | high | `tests/multi_turn/test_false_data_memory_poisoning.py` |
| **F7** | Dormant injection reactivated across turns | high | `tests/multi_turn/test_dormant_injection_reactivation.py` |
| **F8** | Injected instruction executed as a real unauthorized write (~7.5%) | high | `tests/checkers/` · `TestF8InjectedWriteExecuted` |
| **F9** | An independent judge is weaker, not stronger *(cross-check of the judge)* | med | `tests/guardrail/test_independent_judge_calibration.py` |

Two capstones sit on top: a **`PolicyGuard`** that blocks the F7 write at
dispatch (`tests/guardrail/test_action_guard_holds.py`) and an **LLM-judge
content firewall** that catches the answer-channel leak the guard can't
(`tests/guardrail/test_content_firewall_judge.py`).

## If you already do automation QA

Same test / assert / regress loop. Two things change: the system is
non-deterministic, so a finding is a *rate* over N tries, not one pass/fail; and
you assert over a whole trajectory, not one reply.

| Regular automation QA | This agent suite |
|---|---|
| Test case | A task, driven through the agent loop |
| Expected result | A property of the *trace* (right tool, recovered, stopped, grounded) |
| Assertion | A **checker** - a pure function over the `Trace` returning pass/fail + reason |
| Boolean assertion | A rate over N live reps; intermittent shapes locked detector-side |
| Regression test | A strict `xfail` that fails loudly if a known failure mode ever stops happening |
| Golden output | The *end state* (a sandbox file), the only fully deterministic signal |

## The system under test

Kept deliberately small, so the hard software is the *harness*, not the SUT:

- `llm_agent/agent/` - the hand-rolled ReAct loop (`loop.py`), the `Trace` /
  `Step` contract (`trace.py`), a fail-closed `PolicyGuard` over dispatch
  (`guard.py`). Tool failures become in-band error observations, never a crash.
- `llm_agent/tools/` - four mock tools (`calculator`, `file_reader`, `weather`,
  `web_search`) plus a sandboxed `write_file`. Mocked at this boundary so
  failures are injectable deterministically (`injection.py`).
- `llm_agent/providers/` - the only place that issues HTTP. `respx` in tests,
  Ollama live. Every prompt and response logged at `INFO`.
- `llm_agent/checkers/` - the pass/fail deciders over a `Trace`
  (`deterministic.py`, I/O-free) plus the LLM-judge-on-trace (`judge.py`).
  Unit-tested against fixture traces, so a checker bug and an agent bug can't
  contaminate each other.
- `llm_agent/runners/` - drive the agent on a task, capture the raw trace.
- `dataset.py` + `data/tasks.yaml` - the task suite. Tasks in YAML, pass/fail
  logic in test code.

## How to run

The `mocked` tests need nothing external. The `live` tests drive the real agent
against a local **Ollama**:

```sh
ollama serve &            # the LLM backend
ollama pull qwen2.5:7b    # the SUT model (all findings but F2)
ollama pull llama3.2      # second model, only for the F2 float-args probe
```

```sh
uv sync                      # install deps (incl. dev group)
uv run pytest                # all tests; writes a unique reports/report-<UTC>.html
uv run pytest -m mocked      # fast, no backend needed
uv run pytest -m "not live"  # everything except the live-backend tests
uv run pytest -m live        # requires Ollama + qwen2.5:7b
uv run ruff check .          # lint
```

A session fixture warms the model before any live test, so a cold-start load
can't masquerade as an agent failure. The intermittent findings are locked in the
**checkers** against captured traces, so a default run reproduces them
deterministically; the `live` tests assert only what held every rep.

## Reports

Self-contained HTML, with every model prompt and reply captured at `INFO`.

- **[Findings dashboard](https://sbezjak.github.io/llm-agent/reports/findings-dashboard.html)**
  (`reports/findings-dashboard.html`) - all nine modes as severity-striped cards
  with failure-rate meters and captured traces, built by hand from
  `reports/findings.json`. Updated by hand if the numbers change.
- **[Findings report](https://sbezjak.github.io/llm-agent/reports/report-findings.html)**
  (`reports/report-findings.html`) - F1-F9 replayed through the real checkers,
  same every run, no network:
  ```sh
  uv run pytest tests/test_findings_showcase.py \
    -m mocked --html=reports/report-findings.html
  ```
- **[Full run](https://sbezjak.github.io/llm-agent/reports/report-full-live-2026-07-16.html)**
  (`reports/report-full-live-<date>.html`) - the whole suite against the live
  model. The four strict-xfail contracts (F1, F2, F6, F7) show as expected red.
  Regenerate with a bare `uv run pytest --html=reports/report-full-live-<date>.html`.
- **Per-finding evidence** - `reports/findings.json` points each finding at the
  live report it came from and a raw-trace extract under `evidence/`. Every plain
  `uv run pytest` writes a throwaway, gitignored `reports/report-<UTC>.html`, so
  no run can overwrite another (enforced in `conftest.py`).

## Further reading

- [OWASP Top 10 for LLM Applications 2025](https://genai.owasp.org/resource/owasp-top-10-for-llm-applications-2025/)
  - LLM06 Excessive Agency (F5, F7), LLM01 injection (F5, F6, F7).
- [OWASP Top 10 for Agentic Applications](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/)
  - the "semantic firewall" control the two capstones approximate.
- [MITRE ATLAS](https://atlas.mitre.org) - an ATT&CK-style threat matrix for ML.
- [tau-bench](https://github.com/sierra-research/tau-bench), WebArena, SWE-bench,
  AgentBench - the task-suite-with-checkable-success-criteria approach at scale.
- [Anthropic - Building Effective Agents](https://www.anthropic.com/research/building-effective-agents)
  - the workflow-vs-agent distinction; this SUT is the latter, minimal.

Built session by session with Claude Code against a written scope plan;
`CLAUDE.md` is the standing instruction set.
