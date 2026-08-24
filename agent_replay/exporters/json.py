"""JSON exporter.

Produces a single self-describing object with the run and its ordered steps, matching the
shapes in whitepaper §5.1 / §5.2.
"""

from __future__ import annotations

from collections.abc import Iterable

from ..schema import SCHEMA_VERSION, Run, Step


def export_run(run: Run, steps: Iterable[Step]) -> dict:
    """Return a JSON-serializable dict for ``run`` and its ``steps``."""
    return {
        "schema_version": run.schema_version or SCHEMA_VERSION,
        "run": run.to_dict(),
        "steps": [s.to_dict() for s in steps],
    }
