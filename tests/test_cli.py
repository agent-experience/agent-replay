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
