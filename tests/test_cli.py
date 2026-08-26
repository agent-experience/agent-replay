import json

from typer.testing import CliRunner

from agent_replay import event, trace
from agent_replay.cli.main import app

runner = CliRunner()


def _seed(db_path):
    store = None
    from agent_replay.store import Store

    store = Store(db_path)
    with trace("cli-agent", task="do it", store=store) as run:
        event.tool_call(name="crm.update", input={"x": 1}, output={"error": "bad"}, error="bad")
    store.close()
    return run.run_id


def test_list_shows_recorded_run(db_path):
    _seed(db_path)
    result = runner.invoke(app, ["list", "--db", str(db_path)])
    assert result.exit_code == 0
    assert "cli-agent" in result.stdout


def test_list_empty_db(db_path):
    result = runner.invoke(app, ["list", "--db", str(db_path)])
    assert result.exit_code == 0
    assert "No runs recorded yet" in result.stdout


def test_show_latest(db_path):
    _seed(db_path)
    result = runner.invoke(app, ["show", "latest", "--db", str(db_path)])
    assert result.exit_code == 0
    assert "crm.update" in result.stdout


def test_show_missing_run_exits_nonzero(db_path):
    _seed(db_path)
    result = runner.invoke(app, ["show", "run_missing", "--db", str(db_path)])
    assert result.exit_code == 1


def test_replay_latest(db_path):
    _seed(db_path)
    result = runner.invoke(app, ["replay", "latest", "--db", str(db_path)])
    assert result.exit_code == 0
    assert "playback replay" in result.stdout
    assert "Replayed 1 steps" in result.stdout


def test_export_json_is_valid(db_path):
    run_id = _seed(db_path)
    result = runner.invoke(app, ["export", "latest", "--format", "json", "--db", str(db_path)])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["run"]["run_id"] == run_id


def test_export_otlp_is_valid(db_path):
    _seed(db_path)
    result = runner.invoke(app, ["export", "latest", "--format", "otlp", "--db", str(db_path)])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert "resourceSpans" in payload


def test_export_unknown_format_errors(db_path):
    _seed(db_path)
    result = runner.invoke(app, ["export", "latest", "--format", "xml", "--db", str(db_path)])
    assert result.exit_code == 2


def test_export_to_file(db_path, tmp_path):
    _seed(db_path)
    out = tmp_path / "run.json"
    result = runner.invoke(
        app, ["export", "latest", "--format", "json", "--output", str(out), "--db", str(db_path)]
    )
    assert result.exit_code == 0
    assert json.loads(out.read_text())["run"]["agent_name"] == "cli-agent"


_TRACE_JSON = {
    "schema_version": "0.1",
    "run": {"run_id": "run_imported01", "agent_name": "ts-agent", "task": "hi", "status": "failed"},
    "steps": [
        {"step_id": "tool_call_1", "run_id": "run_imported01", "type": "tool_call",
         "name": "get_weather", "input": {"city": "Zzyzx"}, "error": "no station"},
        {"step_id": "llm_call_2", "run_id": "run_imported01", "type": "llm_call",
         "output": {"role": "assistant", "content": "Done!"}},
    ],
}


def test_import_roundtrip_from_file(db_path, tmp_path):
    src = tmp_path / "trace.json"
    src.write_text(json.dumps(_TRACE_JSON))
    result = runner.invoke(app, ["import", str(src), "--db", str(db_path)])
    assert result.exit_code == 0
    assert "run_imported01" in result.stdout
    # The imported run is now a first-class citizen: show + analyze work on it.
    shown = runner.invoke(app, ["show", "run_imported01", "--db", str(db_path)])
    assert shown.exit_code == 0
    assert "get_weather" in shown.stdout


def test_import_export_symmetry(db_path, tmp_path):
    run_id = _seed(db_path)
    exported = runner.invoke(app, ["export", run_id, "--format", "json", "--db", str(db_path)])
    other_db = tmp_path / "other.db"
    src = tmp_path / "exp.json"
    src.write_text(exported.stdout)
    result = runner.invoke(app, ["import", str(src), "--db", str(other_db)])
    assert result.exit_code == 0
    assert run_id in result.stdout


def test_import_existing_run_requires_overwrite(db_path, tmp_path):
    src = tmp_path / "trace.json"
    src.write_text(json.dumps(_TRACE_JSON))
    assert runner.invoke(app, ["import", str(src), "--db", str(db_path)]).exit_code == 0
    # Second import of the same run_id errors...
    dup = runner.invoke(app, ["import", str(src), "--db", str(db_path)])
    assert dup.exit_code == 1
    # ...unless --overwrite is passed, and it does not duplicate steps.
    forced = runner.invoke(app, ["import", str(src), "--overwrite", "--db", str(db_path)])
    assert forced.exit_code == 0
    from agent_replay.store import Store

    store = Store(db_path)
    assert len(store.get_steps("run_imported01")) == 2
    store.close()


def test_import_rejects_unknown_step_type(db_path, tmp_path):
    bad = {"run": {"run_id": "run_bad01", "agent_name": "x"},
           "steps": [{"step_id": "s1", "run_id": "run_bad01", "type": "not_a_type"}]}
    src = tmp_path / "bad.json"
    src.write_text(json.dumps(bad))
    result = runner.invoke(app, ["import", str(src), "--db", str(db_path)])
    assert result.exit_code == 1


def test_import_invalid_json_errors(db_path, tmp_path):
    src = tmp_path / "bad.json"
    src.write_text("{not json")
    result = runner.invoke(app, ["import", str(src), "--db", str(db_path)])
    assert result.exit_code == 2
