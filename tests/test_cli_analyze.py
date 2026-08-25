"""CLI tests for `analyze`, `stats`, and `sanitize`."""

from __future__ import annotations

import json
import sys

from typer.testing import CliRunner

from agent_replay import event, trace
from agent_replay.analysis import clear_registry
from agent_replay.cli.main import app
from agent_replay.store import Store

runner = CliRunner()


def _seed_failure(db_path):
    store = Store(db_path)
    with trace("support-agent", task="close ticket", store=store) as run:
        event.tool_call(
            name="ticket.update", input={"id": "T-9"}, output={"error": "locked"}, error="locked"
        )
        event.llm_call(provider="openai", model="gpt-5.5",
                       input_messages=[{"role": "tool", "content": "locked"}],
                       output_message={"role": "assistant", "content": "Done, ticket closed."})
    store.close()
    return run.run_id


def _seed_clean(db_path):
    store = Store(db_path)
    with trace("ok-agent", task="greet", store=store):
        event.llm_call(
            provider="openai", model="gpt-5.5", input_messages=[], output_message={"content": "hi"}
        )
    store.close()


def test_analyze_text_report(db_path):
    _seed_failure(db_path)
    result = runner.invoke(app, ["analyze", "latest", "--db", str(db_path)])
    assert result.exit_code == 0
    assert "Likely root cause" in result.stdout
    assert "ignored_tool_result" in result.stdout
    assert "Suggested replay point" in result.stdout


def test_analyze_json(db_path):
    run_id = _seed_failure(db_path)
    result = runner.invoke(app, ["analyze", "latest", "--format", "json", "--db", str(db_path)])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["run_id"] == run_id
    assert payload["success"] is False
    assert "ignored_tool_result" in payload["failure_types"]
    assert payload["suggested_replay_step"] is not None


def test_analyze_clean_run(db_path):
    _seed_clean(db_path)
    result = runner.invoke(app, ["analyze", "latest", "--db", str(db_path)])
    assert result.exit_code == 0
    assert "No failures detected" in result.stdout


def test_stats(db_path):
    _seed_failure(db_path)
    _seed_clean(db_path)
    result = runner.invoke(app, ["stats", "--db", str(db_path)])
    assert result.exit_code == 0
    assert "2" in result.stdout  # 2 runs
    assert "ignored_tool_result" in result.stdout


def test_stats_json(db_path):
    _seed_failure(db_path)
    result = runner.invoke(app, ["stats", "--format", "json", "--db", str(db_path)])
    assert result.exit_code == 0
    agg = json.loads(result.stdout)
    assert agg["total_runs"] == 1


def test_analyze_plugin_loads_custom_detector(db_path, tmp_path, monkeypatch):
    plugin = tmp_path / "my_plugin.py"
    plugin.write_text(
        "from agent_replay.analysis import register_detector, Finding, taxonomy\n"
        "@register_detector('my_custom')\n"
        "def d(run, steps):\n"
        "    return [Finding(failure_type=taxonomy.LOOP_DETECTED, detector='my_custom',\n"
        "                    message='custom hit')]\n"
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    _seed_clean(db_path)
    try:
        result = runner.invoke(
            app, ["analyze", "latest", "--plugin", "my_plugin", "--db", str(db_path)]
        )
        assert result.exit_code == 0, result.stdout
        assert "custom hit" in result.stdout
    finally:
        clear_registry()
        sys.modules.pop("my_plugin", None)


def test_sanitize_scrubs_secrets(db_path):
    store = Store(db_path)
    with trace("agent", task="login", store=store):
        event.tool_call(
            name="auth.login",
            input={"user": "alice", "password": "hunter2"},
            output={"ok": True},
        )
    store.close()
    result = runner.invoke(app, ["sanitize", "latest", "--db", str(db_path)])
    assert result.exit_code == 0
    assert "hunter2" not in result.stdout
    assert "alice" in result.stdout  # non-secret fields are preserved
