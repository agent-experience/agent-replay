from agent_replay import event, trace
from agent_replay.redaction import RedactionConfig


def test_metadata_only_drops_bodies_but_keeps_structure(store, monkeypatch):
    monkeypatch.setenv("AGENT_REPLAY_METADATA_ONLY", "1")
    with trace("agent-a", store=store) as run:
        event.tool_call(name="t", input={"secret": "shh"}, output={"pii": "x"})
    step = store.get_steps(run.run_id)[0]
    assert step.name == "t"  # structure kept
    assert step.input == {"_redacted": "metadata_only"}
    assert step.output == {"_redacted": "metadata_only"}


def test_capture_bodies_false_also_redacts(monkeypatch):
    monkeypatch.setenv("AGENT_REPLAY_CAPTURE_BODIES", "0")
    cfg = RedactionConfig.from_env()
    assert cfg.drops_bodies is True
    out = cfg.apply({"input": {"a": 1}, "output": None, "state_before": None, "state_after": None})
    assert out["input"] == {"_redacted": "metadata_only"}


def test_custom_redaction_hook(store):
    def scrub(fields):
        if isinstance(fields.get("input"), dict):
            fields["input"] = {k: "***" for k in fields["input"]}
        return fields

    with trace("agent-a", store=store, redact=scrub) as run:
        event.tool_call(name="t", input={"api_key": "sk-123"})
    step = store.get_steps(run.run_id)[0]
    assert step.input == {"api_key": "***"}
