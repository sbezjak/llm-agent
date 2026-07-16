# CLAUDE.md

## Project

Pytest-based **agent test suite**. Unlike the earlier red-team project in this
portfolio (which attacked an existing service), this project **builds its own
SUT**: a mini **ReAct** agent with 3-4 mock tools (calculator, weather-API
mock, file reader, web-search mock). The theme is testing a system that doesn't just answer
once but *plans, calls tools, and acts over several steps* - the bug is in
the **chain**, not a single response. Tests assert over the full **trace of
tool calls**, not just the final answer.

Python 3.11+, managed with `uv`. Package layout under `llm_agent/` (pin in
`pyproject.toml` `packages = [...]` for the wheel build). The seams:

- `agent/`, the mini ReAct agent under test (plan → tool call → observe loop).
- `tools/`, the 3-4 mock tools. Mock at this boundary so tests can inject
  failures (tool errors, slow tools, conflicting outputs) deterministically.
- `providers/`, adapter over the LLM backend. Only place that issues HTTP
  calls; tests mock here with `respx`.
- `runners/`, drive the agent on a task and capture the raw trace.
- `detectors/` or `checkers/`, decide pass/fail over the trace (right tool?
  recovered from error? stopped vs looped? reconciled conflicting tools?
  timed out gracefully?). A detector seam pointed at a trajectory instead of
  a single reply. I/O-free except an LLM-judge-on-trace.
- `dataset.py`, loads + validates the task suite under `data/`.

## Commands

Use `uv` for all environment and execution tasks:

- Install / sync deps: `uv sync`
- Run all tests: `uv run pytest`
- Run only fast (mocked) tests: `uv run pytest -m mocked`
- Skip live tests: `uv run pytest -m "not live"`
- HTML report: every `uv run pytest` writes a UNIQUE `reports/report-<UTC
  timestamp>.html` (conftest auto-rewrites the default so no run overwrites
  another - a structural guarantee). A report to COMMIT/host
  is generated with an explicit descriptive name.
- Lint: `uv run ruff check .`  Format: `uv run ruff format .`

## Test conventions (configured in pyproject.toml)

- `asyncio_mode = "auto"`, async tests do not need `@pytest.mark.asyncio`.
- Markers gate environment-dependent tests:
  - `@pytest.mark.live`, slow, requires the live LLM backend.
  - `@pytest.mark.mocked`, uses `respx` to mock; default for unit tests.
- `testpaths = ["tests"]`; `ruff` line length 100, target `py311`.

Test categories mirror the **five things you test in an agent**, created as
each lands:

- `tests/outcome/`, did the world end up correct (final state, deterministic).
- `tests/trajectory/`, did it take the right steps (searched before
  answering, never called delete, recovered after a tool error).
- `tests/tool_use/`, right tool / right args / right time; no hallucinated or
  over-calling.
- `tests/multi_turn/`, bugs only visible across turns - context accumulates,
  a poisoned earlier turn trusted later. Where the deferred Crescendo-style
  attacks land.
- `tests/excessive_agency/`, OWASP LLM06 - the agent does more than asked,
  acts on an injected instruction, over-broad tool permissions.

Use the `xfail(strict=True)`-as-contract pattern to lock
in *known* failure modes: a strict xfail that fails loudly if the failure
ever stops happening, forcing acknowledgment instead of silent drift.

## Architecture intent

Preserve these seams when adding code:

- HTTP calls only inside `providers/`. Tests mock here with `respx`.
- Tools mocked at the `tools/` boundary so failures (error, slow, conflicting
  output) are injectable and tests stay deterministic.
- Agent construction / task setup has no live network - deterministic given
  the mocked tools + provider.
- Checkers depend on the captured trace but tests inject known traces as
  fixtures, so agent-loop failures and checker failures don't contaminate
  each other.
- Checkers stay I/O-free (an LLM-judge-on-trace detector is the exception, it
  calls a provider).

---

## Working style with this user

- **`human-tasks.md` is the channel for anything only the user can do.**
  Whenever the next step needs the user (post an update, paste a real URL,
  decide a squishy ground-truth call, run an interactive login), append a
  checkbox item to `human-tasks.md` instead of only mentioning it in chat -
  chat scrolls, the file persists. Read it when picking up work. Named
  `human-tasks`, not `tasks`, so it isn't confused with a generic task tool.
- **Prepare drafts/templates for any task the user has to do by hand.**
  When the next step is something only the user can do, prepare a
  fill-in-the-blanks file with the structure pre-built. Don't make the user
  start from a blank page. Reduce the user's task to filling in the squishy
  parts.
- **Capture explanations to `notes.md` when teaching.** When the user asks
  "explain this to me" and the answer is non-trivial (why an agent failure
  mode happens, how a trace checker decides, OWASP LLM Top 10 / LLM06
  mechanics), mirror it (lightly cleaned up) into `notes.md` as reference.
  The chat scrolls; the article stays.
- **Two writing registers, no duplicate copies.** `notes.md` is the dense,
  finding-first record. The teaching / front-door artifacts (the narrated
  walkthrough, `docs/` explainers, README) use the plain, layered voice the
  user likes. Same explanation in two registers drifts out of sync, so the
  registers serve different artifacts, never two copies of one thing.
- **Ground each front-door artifact in the previous projects' versions
  before drafting.** The article, walkthrough, and LinkedIn post come out
  measurably better when the model first reads the *same* artifact from the
  earlier projects (A/B confirmed). Links live in `PORTFOLIO.md`; read the
  LOCAL sibling repos (`../llm-eval-harness/`, `../llm-rag/`,
  `../llm-api-testing/`, `../llm-red/`) - faster, and LinkedIn URLs are
  auth-walled. For a LinkedIn post, match the shipped voice: curiosity /
  first-person hook, one finding told as a story, an easy-case-vs-hard-case
  contrast, no arrows / hashtags / stacked numbers, closing line exactly
  `Automation engineer learning AI testing. Project N of 5. More from the
  series: <link>`.
- **Default to production / best-practice solutions; take the pragmatic
  shortcut only when the trade-off is justified for this project's scope,
  and call the trade-off out explicitly.** Name what the production-grade
  pattern would be, name why we're not doing it here, and write the
  trade-off into `notes.md` so the writeup shows it was a deliberate choice.
- **Validate a new integration cheaply before any long or expensive run.**
  Prove it works on the smallest possible input first (1-2 items, fabricated
  inputs are fine) and confirm the output parses. ALWAYS arm a monitor on
  the log for any run that is not near-instant - grepping for success AND
  failure signatures
  (`500|Internal Server Error|Traceback|Error|Exception|Killed|OOM|NaN|Timeout|Failed`)
  so a mid-run failure surfaces at the failing job. Smoke test first, monitor
  second, both every time. When a run fails, fix the root cause and
  re-validate cheaply before re-running full.
- **Always make model prompts and responses visible in test reports.**
  Every component that calls a model (providers, LLM-judge checkers) must log
  the prompt going in and the response coming out at `INFO` level via the
  stdlib `logging` module, not truncated. The always-on pytest-html report
  captures these. For an agent project this is how you read the whole trace,
  not just the final answer.
- **Read the report/logs thoroughly - the raw model output / trace is the
  only ground truth, never conclude from a summary boolean, a count, or a
  keyword/length heuristic when the actual text is available.** Open the
  trace and read it end to end; that reading IS the work, not an optional
  check.
- **Prefer the smallest solution that solves the problem; after writing,
  re-read and cut machinery the task didn't ask for.** Treat the re-read as
  a step: "is half of this scaffolding I invented but nobody asked for?" If
  yes, rewrite it small.
- In all prose (docs, comments, commit messages, PR descriptions), join
  clauses with a single hyphen `-`, a comma, a period, or parentheses. The
  only dash character in written text is a single `-`.
- **Name committed artifacts by finding-id / topic, never by build stage.**
  Evidence files, reports, and code comments use the durable public vocabulary
  (`F1-ablation-schema-example.md`, `baseline-trace-calculator.md`, dated report
  names) from creation - session labels (`S1` / `S3a` / `S5c-P2`) live only in
  the gitignored working notes. Stage labels in committed names force a later
  cleanup pass; set the naming convention before the first evidence/report file
  exists.
- End commit messages at the body. The user is the sole author.
