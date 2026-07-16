import logging

from ..agent import PolicyGuard, Trace, run_agent, run_conversation
from ..providers.base import Provider
from ..providers.ollama import OllamaProvider
from ..tools import ToolRegistry, default_registry

log = logging.getLogger(__name__)

SUT_MODEL = "qwen2.5:7b"


async def run_task(
    task: str,
    provider: Provider | None = None,
    registry: ToolRegistry | None = None,
    max_steps: int = 5,
    tool_timeout_s: float = 10.0,
) -> Trace:
    """Drive the agent on one task and return the captured Trace."""
    # 180s HTTP budget: infra tolerance for a loaded backend (healthy replies
    # already run ~40s; 60s ate 4 calibration reps on 2026-07-10). Distinct
    # from tool_timeout_s, the behavioral budget under test - and NOT a
    # retry, which would mask error-recovery behavior.
    provider = provider or OllamaProvider(model=SUT_MODEL, timeout=180.0)
    registry = registry or default_registry()
    trace = await run_agent(
        task, provider, registry, max_steps=max_steps, tool_timeout_s=tool_timeout_s
    )
    log.info(
        "TRACE task=%r stop=%s steps=%d final_answer=%r",
        task,
        trace.stop_reason.value,
        len(trace.steps),
        trace.final_answer,
    )
    return trace


async def run_conversation_task(
    turns: list[str],
    provider: Provider | None = None,
    registry: ToolRegistry | None = None,
    max_steps: int = 5,
    tool_timeout_s: float = 10.0,
    guard: PolicyGuard | None = None,
) -> tuple[Trace, ...]:
    """Drive the agent across several user turns on one threaded transcript and
    return the per-turn Traces. The runner analog of run_task for the multi_turn
    dimension - same default provider/registry, so mocked tests intercept the
    same localhost seam. An optional PolicyGuard fails closed on tool calls
    outside the task's allowlist (the guardrail capstone); guard=None is unchanged."""
    provider = provider or OllamaProvider(model=SUT_MODEL, timeout=180.0)
    registry = registry or default_registry()
    traces = await run_conversation(
        turns, provider, registry, max_steps=max_steps, tool_timeout_s=tool_timeout_s, guard=guard
    )
    for i, trace in enumerate(traces):
        log.info(
            "TURN %d: task=%r stop=%s steps=%d final_answer=%r",
            i,
            trace.task,
            trace.stop_reason.value,
            len(trace.steps),
            trace.final_answer,
        )
    return traces
