"""Redaction / privacy controls (whitepaper §15.3).

Agent Replay is local-first: traces stay on disk and are never uploaded. Still, a trace
can contain prompts, tool results, PII, and secrets. ``RedactionConfig`` lets a developer
drop bodies entirely (metadata-only mode), scrub them with a custom hook, or strip fields
whose key matches a pattern before they are persisted.

Environment variables:
  AGENT_REPLAY_METADATA_ONLY   truthy -> keep step structure but drop body payloads
  AGENT_REPLAY_CAPTURE_BODIES  falsy  -> same effect as metadata-only

``.agent-replayignore``
  A file (in the current directory or ``AGENT_REPLAY_HOME``) with one glob pattern per line.
  Any dict key matching a pattern (case-insensitive :func:`fnmatch`) is redacted, at any
  depth. Blank lines and ``#`` comments are ignored. The ``sanitize`` CLI command additionally
  applies :data:`DEFAULT_SECRET_PATTERNS` before export.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass, field
from fnmatch import fnmatch
from pathlib import Path
from typing import Any

# Step fields that may carry sensitive payloads.
SENSITIVE_KEYS = ("input", "output", "state_before", "state_after")

# Common secret-bearing key patterns, always scrubbed by the `sanitize` command.
DEFAULT_SECRET_PATTERNS = (
    "*password*",
    "*passwd*",
    "*secret*",
    "*token*",
    "*api_key*",
    "*apikey*",
    "*access_key*",
    "*credential*",
    "authorization",
    "cookie",
    "*ssn*",
)

_REDACTED = {"_redacted": "metadata_only"}
_REDACTED_FIELD = "«redacted»"

IGNORE_FILENAME = ".agent-replayignore"


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def load_ignore_patterns(start_dir: str | Path | None = None) -> tuple[str, ...]:
    """Load key patterns from ``.agent-replayignore`` (cwd and ``AGENT_REPLAY_HOME``)."""
    candidates: list[Path] = []
    base = Path(start_dir).expanduser() if start_dir else Path.cwd()
    candidates.append(base / IGNORE_FILENAME)
    home = os.environ.get("AGENT_REPLAY_HOME")
    if home:
        candidates.append(Path(home).expanduser() / IGNORE_FILENAME)

    patterns: list[str] = []
    for path in candidates:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        for line in text.splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                patterns.append(line.lower())
    # De-duplicate while preserving order.
    return tuple(dict.fromkeys(patterns))


def _matches(key: str, patterns: tuple[str, ...]) -> bool:
    key = key.lower()
    return any(fnmatch(key, pat) for pat in patterns)


def scrub(value: Any, patterns: tuple[str, ...]) -> Any:
    """Recursively replace values under keys matching ``patterns`` with a redaction marker."""
    if not patterns:
        return value
    if isinstance(value, dict):
        return {
            k: (_REDACTED_FIELD if _matches(str(k), patterns) else scrub(v, patterns))
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [scrub(v, patterns) for v in value]
    return value


@dataclass
class RedactionConfig:
    capture_bodies: bool = True
    metadata_only: bool = False
    # Optional user hook: receives the dict of sensitive fields, returns a scrubbed dict.
    hook: Callable[[dict], dict] | None = None
    # Key patterns from .agent-replayignore (redacted at any depth).
    ignore_patterns: tuple[str, ...] = field(default_factory=tuple)

    @classmethod
    def from_env(cls, hook: Callable[[dict], dict] | None = None) -> RedactionConfig:
        return cls(
            capture_bodies=_env_bool("AGENT_REPLAY_CAPTURE_BODIES", True),
            metadata_only=_env_bool("AGENT_REPLAY_METADATA_ONLY", False),
            hook=hook,
            ignore_patterns=load_ignore_patterns(),
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
        elif self.ignore_patterns:
            for key in SENSITIVE_KEYS:
                if out.get(key) is not None:
                    out[key] = scrub(out[key], self.ignore_patterns)
        if self.hook is not None:
            out = self.hook(out)
        return out
