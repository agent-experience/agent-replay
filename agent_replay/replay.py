"""Playback replay (Phase 1).

Phase 1 supports **playback replay only**: re-emitting a recorded trajectory in order,
*without* calling any model, tool, retriever, or external API. Mocked replay (Phase 2) and
forked replay (Phase 3) build on this later.
"""

from __future__ import annotations

from collections.abc import Iterator

from .schema import Run, Step
from .store import Store


class PlaybackReplay:
    """Deterministic re-emission of a recorded run's steps."""

    def __init__(self, run_id: str, store: Store | None = None) -> None:
        self.store = store or Store()
        run = self.store.get_run(run_id)
        if run is None:
            raise KeyError(f"run not found: {run_id}")
        self.run: Run = run
        self._steps: list[Step] = self.store.get_steps(run_id)

    def steps(self) -> Iterator[Step]:
        """Yield the recorded steps in order. No external calls are made."""
        yield from self._steps

    def __iter__(self) -> Iterator[Step]:
        return self.steps()

    def __len__(self) -> int:
        return len(self._steps)

    def verify(self) -> bool:
        """Confirm playback matches the stored trace exactly (determinism check)."""
        fresh = self.store.get_steps(self.run.run_id)
        return [s.to_dict() for s in fresh] == [s.to_dict() for s in self._steps]
