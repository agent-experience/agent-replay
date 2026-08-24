"""The ``trace()`` entry point.

Use it as a context manager::

    from agent_replay import trace, event

    with trace("research-agent", task="Find latest pricing"):
        event.llm_call(...)

or as a decorator::

    @trace("research-agent")
    def run_agent(): ...

On enter it creates a :class:`~agent_replay.schema.Run` (status ``running``) and writes it
immediately; on exit it stamps ``ended_at`` / ``latency_ms`` and sets the status to
``failed`` if the block raised, otherwise ``success``. Exceptions always propagate.
"""

from __future__ import annotations

import functools
import time
from collections.abc import Callable
from pathlib import Path

from . import context
from .redaction import RedactionConfig
from .schema import FAILED, RUNNING, SUCCESS, Run, new_run_id, utc_now_iso
from .store import Store


class trace:
    """Context manager + decorator that records one agent run."""

    def __init__(
        self,
        agent_name: str,
        task: str | None = None,
        *,
        store: Store | None = None,
        db_path: str | Path | None = None,
        redact: Callable[[dict], dict] | None = None,
        **metadata,
    ) -> None:
        self.agent_name = agent_name
        self.task = task
        self._store = store
        self._db_path = db_path
        self._redact_hook = redact
        self.metadata = metadata
        # Per-activation state (reset every __enter__ so an instance is reusable).
        self._frame: context.TraceFrame | None = None
        self._t0: float | None = None

    def __enter__(self) -> Run:
        store = self._store or Store(self._db_path)
        run = Run(
            run_id=new_run_id(),
            agent_name=self.agent_name,
            task=self.task,
            started_at=utc_now_iso(),
            status=RUNNING,
            metadata=dict(self.metadata),
        )
        store.insert_run(run)
        frame = context.TraceFrame(
            run=run,
            store=store,
            redaction=RedactionConfig.from_env(hook=self._redact_hook),
        )
        context.push_frame(frame)
        self._frame = frame
        self._t0 = time.perf_counter()
        return run

    def __exit__(self, exc_type, exc, tb) -> bool:
        frame = context.pop_frame()
        if frame is None:  # pragma: no cover - defensive
            return False
        run = frame.run
        run.ended_at = utc_now_iso()
        if self._t0 is not None:
            run.latency_ms = int((time.perf_counter() - self._t0) * 1000)
        run.status = FAILED if exc_type is not None else SUCCESS
        frame.store.update_run(run)
        return False  # never suppress exceptions

    def __call__(self, fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            with trace(
                self.agent_name,
                task=self.task,
                store=self._store,
                db_path=self._db_path,
                redact=self._redact_hook,
                **self.metadata,
            ):
                return fn(*args, **kwargs)

        return wrapper
