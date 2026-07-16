from dataclasses import dataclass


@dataclass(frozen=True)
class PolicyGuard:
    """Fail-closed action guard over tool dispatch - the defensive flip of F7,
    and OWASP LLM06's remediation for excessive agency. Any tool call not on the
    task's authorized allowlist is intercepted BEFORE the handler runs and handed
    back as an in-band BLOCKED observation, so it never executes.

    The defensive twin of the acted_only_within checker: that DETECTS an
    out-of-policy call after the fact, this PREVENTS its effect at dispatch time.
    Action-channel only, on purpose - it cannot stop a payload the agent merely
    SAYS (the answer channel), the defense-in-depth gap F7 turns on. Simplified vs
    production: allowlist is tool NAME only, and a block is a plain
    observation, not an audit event or HITL disambiguation prompt.
    """

    authorized: frozenset[str]

    def check(self, name: str) -> str | None:
        """None if the call is allowed to dispatch; otherwise the BLOCKED
        observation to hand back in its place (the handler is not run)."""
        if name in self.authorized:
            return None
        return f"BLOCKED: {name} requires authorization not granted for this task"
