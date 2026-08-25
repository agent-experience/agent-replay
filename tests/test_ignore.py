"""Tests for `.agent-replayignore` support and field scrubbing (Phase-1-deferred items)."""

from __future__ import annotations

from agent_replay import event, trace
from agent_replay.redaction import RedactionConfig, load_ignore_patterns, scrub
from agent_replay.store import Store


def test_scrub_nested_keys():
    data = {
        "password": "x", "user": "y",
        "nested": {"api_key": "k", "name": "n"}, "items": [{"token": "t"}],
    }
    out = scrub(data, ("*password*", "*api_key*", "*token*"))
    assert out["password"] == "«redacted»"
    assert out["user"] == "y"
    assert out["nested"]["api_key"] == "«redacted»"
    assert out["nested"]["name"] == "n"
    assert out["items"][0]["token"] == "«redacted»"


def test_scrub_no_patterns_is_identity():
    data = {"password": "x"}
    assert scrub(data, ()) == data


def test_load_ignore_patterns_from_cwd(tmp_path, monkeypatch):
    (tmp_path / ".agent-replayignore").write_text("# secrets\n*password*\nAUTHORIZATION\n\n")
    monkeypatch.chdir(tmp_path)
    patterns = load_ignore_patterns()
    assert "*password*" in patterns
    assert "authorization" in patterns  # normalized to lowercase


def test_redaction_config_applies_patterns():
    cfg = RedactionConfig(ignore_patterns=("*password*",))
    out = cfg.apply({"input": {"password": "x", "user": "y"}, "output": None,
                     "state_before": None, "state_after": None})
    assert out["input"]["password"] == "«redacted»"
    assert out["input"]["user"] == "y"


def test_ignore_file_scrubs_recorded_trace(tmp_path, monkeypatch):
    (tmp_path / ".agent-replayignore").write_text("*password*\n")
    monkeypatch.chdir(tmp_path)
    db = tmp_path / "traces.db"
    store = Store(db)
    with trace("agent", task="login", store=store) as run:
        event.tool_call(
            name="auth.login",
            input={"user": "alice", "password": "hunter2"},
            output={"ok": True},
        )
    steps = store.get_steps(run.run_id)
    store.close()
    assert steps[0].input["password"] == "«redacted»"
    assert steps[0].input["user"] == "alice"
