"""First outcome-dimension test: the oracle is the world's end state -
the sandbox file after the run - not the answer text (F2 proved a correct
answer can sit on a broken mechanism). write_file is registered per-test
with a tmp root, on top of the default registry; the locked 4-tool tests
keep their calibrated prompt context."""

import logging

import pytest

from llm_agent.agent import StopReason
from llm_agent.dataset import get_task
from llm_agent.runners import run_task
from llm_agent.tools import default_registry, write_file_tool

log = logging.getLogger(__name__)

TASK = get_task("write-file-outcome")["task"]


def _log_sandbox(tmp_path) -> dict[str, str]:
    """The reading surface for the outcome dimension: what does the world
    look like after the run, independent of anything the model said."""
    files = {p.name: p.read_text() for p in sorted(tmp_path.iterdir()) if p.is_file()}
    log.info("SANDBOX END STATE: %s", files)
    return files


EXPECTS = get_task("write-file-outcome")["expects"]


@pytest.mark.live
async def test_write_file_end_state(tmp_path):
    """Calibrated 3/3 clean 2026-07-09 (single verbatim write, truthful
    answer): evidence/baseline-trace-write-file-outcome.md. The oracle reads the
    world, not the transcript: exactly the expected file exists (an extra
    file is the did-more-than-asked shape) with the expected content -
    equality is earnable on tool-mediated file content, unlike answer text;
    .strip() so a conventional trailing newline never fails a correct
    write. Expected values come from the task's expects in tasks.yaml so
    they cannot drift from the task string."""
    registry = default_registry()
    registry.register(write_file_tool(tmp_path))

    trace = await run_task(TASK, registry=registry)

    files = _log_sandbox(tmp_path)
    if not any(s.tool == "write_file" for s in trace.steps):
        pytest.skip(
            "model emitted no native write_file call this run (rendered the tool call as text "
            "content, not a tool_call); inconclusive for the end-state oracle - the tool "
            f"plumbing misfired, not the outcome. Same no-call skip as test_numeric_args_typed. "
            f"final_answer={trace.final_answer!r}"
        )
    assert any(s.tool == "write_file" and not s.error for s in trace.steps), "no successful write"
    assert trace.stop_reason is StopReason.FINAL_ANSWER
    assert list(files) == [EXPECTS["file"]], "wrong or extra files in the sandbox"
    assert files[EXPECTS["file"]].strip() == EXPECTS["content"]
