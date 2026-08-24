from agent_replay.schema import Run, Step
from agent_replay.store import default_db_path


def _run(run_id, started_at, status="running"):
    return Run(run_id=run_id, agent_name="a", started_at=started_at, status=status)


def test_insert_get_and_update_run(store):
    run = _run("run_1", "2026-08-24T00:00:00Z")
    store.insert_run(run)
    assert store.get_run("run_1").status == "running"

    run.status = "success"
    store.update_run(run)
    assert store.get_run("run_1").status == "success"


def test_list_runs_orders_most_recent_first(store):
    store.insert_run(_run("run_old", "2026-08-24T00:00:00Z"))
    store.insert_run(_run("run_new", "2026-08-24T05:00:00Z"))
    runs = store.list_runs()
    assert [r.run_id for r in runs] == ["run_new", "run_old"]
    assert store.latest_run().run_id == "run_new"


def test_steps_preserve_insertion_order(store):
    store.insert_run(_run("run_1", "2026-08-24T00:00:00Z"))
    for i in range(3):
        store.insert_step(Step(step_id=f"tool_call_{i}", run_id="run_1", type="tool_call"))
    steps = store.get_steps("run_1")
    assert [s.step_id for s in steps] == ["tool_call_0", "tool_call_1", "tool_call_2"]


def test_get_missing_run_returns_none(store):
    assert store.get_run("nope") is None
    assert store.latest_run() is None


def test_default_db_path_respects_env(monkeypatch, tmp_path):
    target = tmp_path / "custom.db"
    monkeypatch.setenv("AGENT_REPLAY_DB", str(target))
    assert default_db_path() == target
    monkeypatch.delenv("AGENT_REPLAY_DB")
    monkeypatch.setenv("AGENT_REPLAY_HOME", str(tmp_path))
    assert default_db_path() == tmp_path / "traces.db"


def test_json_columns_round_trip(store):
    store.insert_run(_run("run_1", "2026-08-24T00:00:00Z"))
    store.insert_step(
        Step(step_id="s1", run_id="run_1", type="tool_call", input={"nested": [1, 2, {"x": True}]})
    )
    assert store.get_steps("run_1")[0].input == {"nested": [1, 2, {"x": True}]}
