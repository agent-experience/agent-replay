"""Redaction / privacy controls (whitepaper §15.3, Phase 1 subset).

Agent Replay is local-first: traces stay on disk and are never uploaded. Still, a trace
can contain prompts, tool results, PII, and secrets. ``RedactionConfig`` lets a developer
drop bodies entirely (metadata-only mode) or scrub them with a custom hook before they
are persisted.

Environment variables:
  AGENT_REPLAY_METADATA_ONLY   truthy -> keep step structure but drop body payloads
  AGENT_REPLAY_CAPTURE_BODIES  falsy  -> same effect as metadata-only

Deferred to a later phase (documented as non-blocking): ``.agent-replayignore`` and a
standalone ``sanitize`` command.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass

# Step fields that may carry sensitive payloads.
SENSITIVE_KEYS = ("input", "output", "state_before", "state_after")

_REDACTED = {"_redacted": "metadata_only"}


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class RedactionConfig:
    capture_bodies: bool = True
    metadata_only: bool = False
    # Optional user hook: receives the dict of sensitive fields, returns a scrubbed dict.
    hook: Callable[[dict], dict] | None = None

    @classmethod
    def from_env(cls, hook: Callable[[dict], dict] | None = None) -> RedactionConfig:
        return cls(
            capture_bodies=_env_bool("AGENT_REPLAY_CAPTURE_BODIES", True),
            metadata_only=_env_bool("AGENT_REPLAY_METADATA_ONLY", False),
            hook=hook,
        )

    @property
    def drops_bodies(self) -> bool:
        return self.metadata_only or not self.capture_bodies

    def apply(self, fields: dict) -> dict:
        """Return a redacted copy of the given sensitive ``fields`` dict."""
        out = dict(fields)
        if self.drops_bodies:
            for key in SENSITIVE_KEYS:
                if out.get(key) is not None:
                    out[key] = dict(_REDACTED)
        if self.hook is not None:
            out = self.hook(out)
        return out
