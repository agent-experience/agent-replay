import pytest

from agent_replay import event, trace
from agent_replay.replay import PlaybackReplay


def test_playback_matches_recorded_trace(store):
    with trace("agent-a", store=store) as run:
        event.llm_call(provider="openai", model="m", input_messages=[], output_message={})
        event.tool_call(name="t", input={"x": 1}, output={"ok": True})

    playback = PlaybackReplay(run.run_id, store=store)
    assert len(playback) == 2
    assert [s.step_id for s in playback] == ["llm_call_1", "tool_call_2"]
    assert playback.verify() is True


def test_replay_unknown_run_raises(store):
    with pytest.raises(KeyError):
        PlaybackReplay("run_does_not_exist", store=store)
