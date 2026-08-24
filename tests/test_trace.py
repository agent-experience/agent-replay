import warnings

import pytest

from agent_replay import event, trace
from agent_replay.context import current_frame, depth


def test_trace_records_run_and_steps(store):
    with trace("agent-a", task="do a thing", store=store) as run:
        event.llm_call(provider="openai", model="gpt-5.5", input_messages=[], output_message={})
        event.tool_call(name="t", input={"x": 1}, output={"ok": True})

    saved = store.get_run(run.run_id)
    assert saved.status == "success"
    assert saved.latency_ms is not None
    steps = store.get_steps(run.run_id)
    assert [s.type for s in steps] == ["llm_call", "tool_call"]
    assert [s.step_id for s in steps] == ["llm_call_1", "tool_call_2"]


def test_trace_marks_failed_on_exception_and_reraises(store):
    with pytest.raises(ValueError):
        with trace("agent-a", store=store) as run:
            run_id = run.run_id
            raise ValueError("boom")
    assert store.get_run(run_id).status == "failed"


def test_nested_traces(store):
    with trace("outer", store=store) as outer:
        assert depth() == 1
        event.tool_call(name="outer-tool")
        with trace("inner", store=store) as inner:
            assert depth() == 2
            event.tool_call(name="inner-tool")
        assert current_frame().run.run_id == outer.run_id

    assert [s.name for s in store.get_steps(outer.run_id)] == ["outer-tool"]
    assert [s.name for s in store.get_steps(inner.run_id)] == ["inner-tool"]


def test_event_outside_trace_is_noop_with_warning():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        assert event.tool_call(name="orphan") is None
    assert any("outside an active trace" in str(w.message) for w in caught)


def test_trace_as_decorator(store):
    @trace("decorated-agent", store=store)
    def run_agent():
        event.tool_call(name="t")
        return 42

    assert run_agent() == 42
    assert store.latest_run().agent_name == "decorated-agent"
