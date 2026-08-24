"""Agent Replay — time-travel debugging for AI agents.

Phase 1 public surface: record structured traces of agent runs, store them locally in
SQLite, inspect them from the CLI, replay them (playback), and export to JSON / OTLP.
"""

from __future__ import annotations

from . import event
from .replay import PlaybackReplay
from .schema import SCHEMA_VERSION, Run, Step
from .store import Store
from .trace import trace

__version__ = "0.1.0"

__all__ = [
    "trace",
    "event",
    "Store",
    "Run",
    "Step",
    "PlaybackReplay",
    "SCHEMA_VERSION",
    "__version__",
]
