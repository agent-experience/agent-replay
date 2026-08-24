"""Local SQLite trace store.

Runs are inserted when a ``trace()`` block opens, each step is written as it is recorded,
and the run row is finalized on exit. Writing incrementally means a crashed or failed run
still leaves a fully inspectable trace on disk — which is the whole point for a debugger.

Default location: ``~/.agent-replay/traces.db``. Override with the ``AGENT_REPLAY_DB``
environment variable (full path to the db file) or ``AGENT_REPLAY_HOME`` (directory).
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
from pathlib import Path
from typing import Any

from .schema import Run, Step


def default_db_path() -> Path:
    """Resolve the trace-store path from the environment, falling back to the home dir."""
    env_db = os.environ.get("AGENT_REPLAY_DB")
    if env_db:
        return Path(env_db).expanduser()
    home = os.environ.get("AGENT_REPLAY_HOME")
    base = Path(home).expanduser() if home else Path.home() / ".agent-replay"
    return base / "traces.db"


def _dumps(value: Any) -> str | None:
    if value is None:
        return None
    return json.dumps(value, default=str)


def _loads(value: str | None) -> Any:
    if value is None:
        return None
    return json.loads(value)


class Store:
    """A SQLite-backed store for runs and steps."""

    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = Path(db_path).expanduser() if db_path else default_db_path()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        # Agents may touch the store from worker threads; guard the shared connection.
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._init_schema()

    # -- schema -----------------------------------------------------------------
    def _init_schema(self) -> None:
        with self._lock, self._conn:
            self._conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    agent_name TEXT NOT NULL,
                    task TEXT,
                    started_at TEXT,
                    ended_at TEXT,
                    status TEXT,
                    cost_usd REAL,
                    latency_ms INTEGER,
                    metadata TEXT,
                    schema_version TEXT
                );

                CREATE TABLE IF NOT EXISTS steps (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    step_id TEXT,
                    run_id TEXT NOT NULL,
                    type TEXT,
                    name TEXT,
                    input TEXT,
                    output TEXT,
                    state_before TEXT,
                    state_after TEXT,
                    error TEXT,
                    usage TEXT,
                    parent_step_id TEXT,
                    timestamp TEXT,
                    metadata TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_steps_run ON steps(run_id);
                """
            )

    # -- writes -----------------------------------------------------------------
    def insert_run(self, run: Run) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT OR REPLACE INTO runs "
                "(run_id, agent_name, task, started_at, ended_at, status, "
                " cost_usd, latency_ms, metadata, schema_version) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    run.run_id,
                    run.agent_name,
                    run.task,
                    run.started_at,
                    run.ended_at,
                    run.status,
                    run.cost_usd,
                    run.latency_ms,
                    _dumps(run.metadata),
                    run.schema_version,
                ),
            )

    # Finalizing a run is just re-writing the row; INSERT OR REPLACE handles both.
    update_run = insert_run

    def insert_step(self, step: Step) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO steps "
                "(step_id, run_id, type, name, input, output, state_before, "
                " state_after, error, usage, parent_step_id, timestamp, metadata) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    step.step_id,
                    step.run_id,
                    step.type,
                    step.name,
                    _dumps(step.input),
                    _dumps(step.output),
                    _dumps(step.state_before),
                    _dumps(step.state_after),
                    step.error,
                    _dumps(step.usage),
                    step.parent_step_id,
                    step.timestamp,
                    _dumps(step.metadata),
                ),
            )

    # -- reads ------------------------------------------------------------------
    def _row_to_run(self, row: sqlite3.Row) -> Run:
        return Run(
            run_id=row["run_id"],
            agent_name=row["agent_name"],
            task=row["task"],
            started_at=row["started_at"],
            ended_at=row["ended_at"],
            status=row["status"],
            cost_usd=row["cost_usd"],
            latency_ms=row["latency_ms"],
            metadata=_loads(row["metadata"]) or {},
            schema_version=row["schema_version"],
        )

    def _row_to_step(self, row: sqlite3.Row) -> Step:
        return Step(
            step_id=row["step_id"],
            run_id=row["run_id"],
            type=row["type"],
            name=row["name"],
            input=_loads(row["input"]),
            output=_loads(row["output"]),
            state_before=_loads(row["state_before"]),
            state_after=_loads(row["state_after"]),
            error=row["error"],
            usage=_loads(row["usage"]),
            parent_step_id=row["parent_step_id"],
            timestamp=row["timestamp"],
            metadata=_loads(row["metadata"]) or {},
        )

    def get_run(self, run_id: str) -> Run | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM runs WHERE run_id = ?", (run_id,)
            ).fetchone()
        return self._row_to_run(row) if row else None

    def list_runs(self, limit: int = 50) -> list[Run]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM runs ORDER BY started_at DESC, rowid DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [self._row_to_run(r) for r in rows]

    def latest_run(self) -> Run | None:
        runs = self.list_runs(limit=1)
        return runs[0] if runs else None

    def get_steps(self, run_id: str) -> list[Step]:
        # Ordered by insertion id: monotonic and stable even when timestamps collide.
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM steps WHERE run_id = ? ORDER BY id ASC", (run_id,)
            ).fetchall()
        return [self._row_to_step(r) for r in rows]

    def close(self) -> None:
        with self._lock:
            self._conn.close()
