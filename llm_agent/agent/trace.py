from dataclasses import dataclass
from enum import StrEnum


class StopReason(StrEnum):
    FINAL_ANSWER = "final_answer"  # sentinel: the model replied with no tool calls
    MAX_STEPS = "max_steps"  # hard cap on model calls hit


@dataclass(frozen=True)
class Step:
    """One tool round. The final answer is not a Step, it lives on the Trace."""

    index: int  # 0-based position in the trace
    thought: str  # assistant content alongside the tool call ("" if none)
    tool: str  # tool name the model asked for (may not exist in the registry)
    args: dict  # arguments as passed to the tool
    observation: str  # exactly what was fed back to the model (result or error text)
    error: bool  # observation is an error, not a result
    duration_s: float  # wall-clock time of the tool call


@dataclass(frozen=True)
class Trace:
    task: str
    steps: tuple[Step, ...]
    final_answer: str | None  # None when stopped by the cap
    stop_reason: StopReason  # set by the loop, never derived by checkers
