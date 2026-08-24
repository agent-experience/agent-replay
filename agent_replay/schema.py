"""Trace schema for Agent Replay.

Two record types make up a trace:

- :class:`Run`  — one complete execution of an agent task (whitepaper §5.1).
- :class:`Step` — one meaningful state transition inside a run (§5.2).

Both are plain :mod:`dataclasses` so the SDK stays dependency-light. ``to_dict`` /
``from_dict`` round-trip through JSON, and ``from_dict`` preserves unknown top-level
keys under ``metadata`` so the schema can grow without breaking older readers.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field, fields
from datetime import datetime, timezone
from typing import Any

# Bump when the on-disk / exported trace shape changes in a breaking way.
SCHEMA_VERSION = "0.1"

# Step types recorded in Phase 1.
LLM_CALL = "llm_call"
TOOL_CALL = "tool_call"
RETRIEVAL = "retrieval"
MEMORY_READ = "memory_read"
MEMORY_WRITE = "memory_write"

STEP_TYPES = frozenset({LLM_CALL, TOOL_CALL, RETRIEVAL, MEMORY_READ, MEMORY_WRITE})

# Run.status values.
RUNNING = "running"
SUCCESS = "success"
FAILED = "failed"


def new_run_id() -> str:
    """Return a fresh run id, e.g. ``run_9f3c1a2b4d5e``."""
    return f"run_{uuid.uuid4().hex[:12]}"


def utc_now_iso() -> str:
    """Return the current UTC time as an ISO-8601 string ending in ``Z``."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _split_known(cls: type, data: dict) -> tuple[dict, dict]:
    """Partition ``data`` into (known dataclass fields, everything else)."""
    known_names = {f.name for f in fields(cls)}
    known = {k: v for k, v in data.items() if k in known_names}
    extra = {k: v for k, v in data.items() if k not in known_names}
    return known, extra


@dataclass
class Run:
    """One complete execution of an agent task."""

    run_id: str
    agent_name: str
    task: str | None = None
    started_at: str | None = None
    ended_at: str | None = None
    status: str = RUNNING
    cost_usd: float | None = None
    latency_ms: int | None = None
    metadata: dict = field(default_factory=dict)
    schema_version: str = SCHEMA_VERSION

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "agent_name": self.agent_name,
            "task": self.task,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "status": self.status,
            "cost_usd": self.cost_usd,
            "latency_ms": self.latency_ms,
            "metadata": self.metadata,
            "schema_version": self.schema_version,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Run:
        known, extra = _split_known(cls, data)
        run = cls(**known)
        # Forward-compatibility: keep unknown top-level keys without clobbering metadata.
        for k, v in extra.items():
            run.metadata.setdefault(k, v)
        return run


@dataclass
class Step:
    """One meaningful state transition inside an agent run."""

    step_id: str
    run_id: str
    type: str
    name: str | None = None
    input: Any = None
    output: Any = None
    state_before: Any = None
    state_after: Any = None
    error: str | None = None
    usage: dict | None = None
    parent_step_id: str | None = None
    timestamp: str | None = None
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "step_id": self.step_id,
            "run_id": self.run_id,
            "type": self.type,
            "name": self.name,
            "input": self.input,
            "output": self.output,
            "state_before": self.state_before,
            "state_after": self.state_after,
            "error": self.error,
            "usage": self.usage,
            "parent_step_id": self.parent_step_id,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Step:
        known, extra = _split_known(cls, data)
        step = cls(**known)
        for k, v in extra.items():
            step.metadata.setdefault(k, v)
        return step
