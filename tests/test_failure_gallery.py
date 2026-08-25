"""The failure gallery records one trace per taxonomy type, each detectable (§8.4)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from agent_replay.analysis import analyze, taxonomy
from agent_replay.store import Store

REPO_ROOT = Path(__file__).resolve().parents[1]
GALLERY = REPO_ROOT / "examples" / "failure_gallery" / "main.py"


def test_gallery_covers_every_failure_type(tmp_path):
    db = tmp_path / "gallery.db"
    env = dict(os.environ, AGENT_REPLAY_DB=str(db), PYTHONPATH=str(REPO_ROOT))
    result = subprocess.run(
        [sys.executable, str(GALLERY)], env=env, capture_output=True, text=True, timeout=60
    )
    assert result.returncode == 0, result.stderr

    store = Store(db)
    try:
        runs = store.list_runs(limit=100)
        assert len(runs) == len(taxonomy.FAILURE_TYPES)
        covered = set()
        for run in runs:
            report = analyze(run, store.get_steps(run.run_id))
            tagged = run.metadata.get("failure_type")
            assert tagged in report.failure_types, (
                f"run tagged {tagged} but detected {report.failure_types}"
            )
            covered.add(tagged)
        # Every taxonomy type has a runnable, detectable example trace.
        assert covered == set(taxonomy.FAILURE_TYPES)
    finally:
        store.close()
