import asyncio
import logging
import time

from ..providers.base import AssistantMessage, Provider
from ..tools import ToolRegistry
from .guard import PolicyGuard
from .trace import Step, StopReason, Trace

log = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a helpful assistant. Use the available tools to solve the task. "
    "When you have the answer, reply with it directly instead of calling a tool."
)


async def run_agent(
    task: str,
    provider: Provider,
    registry: ToolRegistry,
    max_steps: int = 5,
    tool_timeout_s: float = 10.0,
    guard: PolicyGuard | None = None,
) -> Trace:
    """Hand-rolled ReAct loop: plan -> tool call -> observe, until the model
    answers without tool calls (sentinel) or max_steps model calls (cap).
    Deterministic given a mocked provider and mocked tools. An optional
    PolicyGuard fails closed on any tool call outside the task's allowlist;
    guard=None leaves dispatch unguarded (the default, unchanged behavior)."""
    messages: list[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": task},
    ]
    return await _run_loop(task, messages, provider, registry, max_steps, tool_timeout_s, guard)


async def run_conversation(
    turns: list[str],
    provider: Provider,
    registry: ToolRegistry,
    max_steps: int = 5,
    tool_timeout_s: float = 10.0,
    guard: PolicyGuard | None = None,
) -> tuple[Trace, ...]:
    """Thread one message array across several user turns. The system prompt is
    seeded once; each turn appends its user message and re-enters the ReAct loop
    over the *accumulated* transcript, so a tool observation from an earlier turn
    stays in context for a later one. That persistence is the multi_turn surface
    - an earlier poisoned turn trusted by a later step. Returns one Trace per
    turn; max_steps and tool_timeout_s are per-turn budgets."""
    messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
    traces: list[Trace] = []
    for turn in turns:
        messages.append({"role": "user", "content": turn})
        trace = await _run_loop(
            turn, messages, provider, registry, max_steps, tool_timeout_s, guard
        )
        traces.append(trace)
    return tuple(traces)


async def _run_loop(
    task: str,
    messages: list[dict],
    provider: Provider,
    registry: ToolRegistry,
    max_steps: int,
    tool_timeout_s: float,
    guard: PolicyGuard | None = None,
) -> Trace:
    """Run the ReAct loop over an existing message array, appending every
    assistant and tool message to it in place so a caller can thread state
    across turns (run_conversation). `steps` is per-call - index 0-based within
    this loop - while `messages` persists. Returns the Trace for this call."""
    steps: list[Step] = []
    for _ in range(max_steps):
        reply = await provider.chat(messages, registry.specs())
        if not reply.tool_calls:  # sentinel wins, checked before the cap can bite
            # Append the answer so a later turn sees it; run_agent discards
            # messages after, so this is invisible there and load-bearing here.
            messages.append({"role": "assistant", "content": reply.content})
            return Trace(task, tuple(steps), reply.content, StopReason.FINAL_ANSWER)
        messages.append(_assistant_message(reply))
        for call in reply.tool_calls:
            observation, error, duration_s = await _execute(
                registry, call.name, call.args, tool_timeout_s, guard
            )
            log.info(
                "STEP %d: tool=%s args=%s error=%s observation:\n%s",
                len(steps),
                call.name,
                call.args,
                error,
                observation,
            )
            messages.append({"role": "tool", "tool_name": call.name, "content": observation})
            steps.append(
                Step(
                    len(steps), reply.content, call.name, call.args, observation, error, duration_s
                )
            )
    return Trace(task, tuple(steps), None, StopReason.MAX_STEPS)


async def _execute(
    registry: ToolRegistry,
    name: str,
    args: dict,
    timeout_s: float,
    guard: PolicyGuard | None = None,
) -> tuple[str, bool, float]:
    """Run one tool call under a per-call time budget. Any failure (unauthorized,
    unknown tool, bad args, tool raised, timed out) becomes an error observation
    the model sees, never an exception - a hallucinated tool call must produce an
    observable step, not a crash. The guard fails closed FIRST, before dispatch:
    a blocked call never reaches the handler, but still returns an observation
    (error=True) so the attempt is recorded as a Step, not silently dropped."""
    if guard is not None:
        blocked = guard.check(name)
        if blocked is not None:
            return blocked, True, 0.0
    tool = registry.get(name)
    if tool is None:
        return f"error: unknown tool {name!r}", True, 0.0
    start = time.monotonic()
    try:
        result = await asyncio.wait_for(tool.handler(**args), timeout_s)
        return result, False, time.monotonic() - start
    except TimeoutError:
        message = f"error: tool {name!r} timed out after {timeout_s}s"
        return message, True, time.monotonic() - start
    except Exception as exc:
        return f"error: {exc}", True, time.monotonic() - start


def _assistant_message(reply: AssistantMessage) -> dict:
    return {
        "role": "assistant",
        "content": reply.content,
        "tool_calls": [
            {"function": {"name": call.name, "arguments": call.args}} for call in reply.tool_calls
        ],
    }
