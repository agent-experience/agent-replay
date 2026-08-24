from agent_replay.schema import SCHEMA_VERSION, Run, Step, new_run_id, utc_now_iso


def test_run_id_and_timestamp_formats():
    assert new_run_id().startswith("run_")
    assert utc_now_iso().endswith("Z")


def test_run_round_trip():
    run = Run(run_id="run_1", agent_name="a", task="t", status="success", latency_ms=12)
    assert Run.from_dict(run.to_dict()) == run
    assert run.schema_version == SCHEMA_VERSION


def test_step_round_trip():
    step = Step(
        step_id="tool_call_1",
        run_id="run_1",
        type="tool_call",
        name="crm.update",
        input={"a": 1},
        output={"error": "bad"},
        error="bad",
        usage={"input_tokens": 5},
    )
    assert Step.from_dict(step.to_dict()) == step


def test_from_dict_preserves_unknown_keys_in_metadata():
    run = Run.from_dict({"run_id": "r", "agent_name": "a", "future_field": 99})
    assert run.metadata["future_field"] == 99
