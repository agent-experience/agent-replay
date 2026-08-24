"""Run each example end-to-end (as a subprocess) and assert it recorded a trace."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from agent_replay.store import Store

REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLES_DIR = REPO_ROOT / "examples"

# name -> expected recorded step types (in order)
EXAMPLES = {
    "minimal_openai_agent": ["llm_call", "tool_call", "llm_call"],
    "failed_tool_call": ["llm_call", "tool_call"],
    "bad_retrieval": ["retrieval", "llm_call"],
    "ignored_tool_result": ["tool_call", "llm_call"],
}


@pytest.mark.parametrize("name,expected_types", EXAMPLES.items())
def test_example_records_expected_trace(name, expected_types, tmp_path):
    db = tmp_path / f"{name}.db"
    env = dict(os.environ, AGENT_REPLAY_DB=str(db), PYTHONPATH=str(REPO_ROOT))
    script = EXAMPLES_DIR / name / "main.py"

    result = subprocess.run(
        [sys.executable, str(script)],
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr

    store = Store(db)
    try:
        run = store.latest_run()
        assert run is not None
        assert run.status == "success"
        steps = store.get_steps(run.run_id)
        assert [s.type for s in steps] == expected_types
    finally:
        store.close()
