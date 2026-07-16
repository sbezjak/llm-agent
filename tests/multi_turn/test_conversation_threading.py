"""Multi-turn plumbing contract. Before any injection probe:
prove that run_conversation actually threads one transcript across user turns,
so a later turn sees an earlier turn's state. Without this, a multi_turn finding
("turn 2 trusted turn 1's poisoned observation") could be an artifact of a
broken harness, not the agent - the same discipline the single-turn tool tests used to pin that a
payload provably arrived before judging the agent's response to it.

This test scripts the model, so it asserts the loop's message-threading, not any
model behavior. The poisoned-observation probe and its cross-turn oracle land in
chunk 2.
"""

import json
import logging

import pytest
import respx

from llm_agent.agent import StopReason
from llm_agent.runners import run_conversation_task

log = logging.getLogger(__name__)

# Turn 1: a tool call then an answer (two chat replies). Turn 2: a direct answer
# (one chat reply). script_chat consumes these in order across the whole
# conversation, so the count pins that the loop re-enters per turn.
_CALC = {
    "role": "assistant",
    "content": "Let me compute that.",
    "tool_calls": [{"function": {"name": "calculator", "arguments": {"expression": "2 + 2"}}}],
}
_ANSWER_1 = {"role": "assistant", "content": "2 plus 2 is 4."}
_ANSWER_2 = {"role": "assistant", "content": "You asked me what 2 plus 2 is."}


@pytest.mark.mocked
@respx.mock
async def test_conversation_threads_state_across_turns(script_chat):
    """Turn 1 calls the calculator and answers; turn 2 answers directly. The
    per-turn Trace shape is pinned, and turn 2's chat request must carry turn 1's
    user message, its tool observation, and its answer - the accumulation that
    makes an earlier turn reachable by a later one."""
    route = script_chat(_CALC, _ANSWER_1, _ANSWER_2)

    traces = await run_conversation_task(["What is 2 plus 2?", "What did I just ask you?"])

    # One Trace per turn, each the expected shape.
    assert len(traces) == 2
    t1, t2 = traces
    assert [s.tool for s in t1.steps] == ["calculator"]
    assert t1.steps[0].observation == "4"
    assert t1.stop_reason is StopReason.FINAL_ANSWER
    assert t1.final_answer == "2 plus 2 is 4."
    assert t2.steps == ()
    assert t2.stop_reason is StopReason.FINAL_ANSWER
    assert t2.final_answer == "You asked me what 2 plus 2 is."

    # Threading proof: the last chat call (turn 2) saw turn 1's whole transcript.
    turn2_messages = json.loads(route.calls[-1].request.content)["messages"]
    systems = [m for m in turn2_messages if m.get("role") == "system"]
    assert len(systems) == 1, "system prompt must be seeded once for the whole conversation"
    joined = " ".join(m.get("content", "") for m in turn2_messages)
    assert "What is 2 plus 2?" in joined  # turn 1 user message persisted
    assert "2 plus 2 is 4." in joined  # turn 1 answer persisted
    assert "What did I just ask you?" in joined  # turn 2 user message present
    assert any(m.get("role") == "tool" and m.get("content") == "4" for m in turn2_messages), (
        "turn 1's tool observation must persist into turn 2's context"
    )
