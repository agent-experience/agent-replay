"""Unit tests for each deterministic detector (whitepaper §8.4: every detector tested)."""

from __future__ import annotations

from agent_replay.analysis import taxonomy
from agent_replay.analysis.detectors import (
    detect_bad_retrieval,
    detect_context_pollution,
    detect_excessive_retry,
    detect_final_answer_conflict,
    detect_hallucinated_tool_argument,
    detect_ignored_tool_result,
    detect_loop,
    detect_permission_mismatch,
    detect_stale_memory,
    detect_unsafe_write_action,
)
from agent_replay.schema import Run, Step

_N = {"n": 0}


def mkrun(status: str = "success", **metadata) -> Run:
    return Run(run_id="run_test", agent_name="agent", status=status, metadata=metadata)


def mkstep(step_type: str, name: str | None = None, **kwargs) -> Step:
    _N["n"] += 1
    return Step(
        step_id=f"{step_type}_{_N['n']}", run_id="run_test", type=step_type, name=name, **kwargs
    )


def types(findings) -> set[str]:
    return {f.failure_type for f in findings}


def test_hallucinated_tool_argument():
    steps = [
        mkstep("tool_call", "crm.update", input={"refund_status": "x"},
               error="field refund_status is deprecated")
    ]
    findings = detect_hallucinated_tool_argument(mkrun(), steps)
    assert types(findings) == {taxonomy.HALLUCINATED_TOOL_ARGUMENT}
    # A clean tool error unrelated to schema should not fire.
    clean = [mkstep("tool_call", "t", error="network timeout")]
    assert detect_hallucinated_tool_argument(mkrun(), clean) == []


def test_ignored_tool_result():
    steps = [
        mkstep("tool_call", "ticket.update", output={"error": "locked"}, error="locked"),
        mkstep("llm_call", "gpt", output={"role": "assistant", "content": "Done, all set."}),
    ]
    findings = detect_ignored_tool_result(mkrun(status="success"), steps)
    assert types(findings) == {taxonomy.IGNORED_TOOL_RESULT}


def test_ignored_tool_result_not_flagged_when_recovered():
    steps = [
        mkstep("tool_call", "t", error="boom"),
        mkstep("tool_call", "t", output={"ok": True}),  # retried and succeeded
    ]
    assert detect_ignored_tool_result(mkrun(), steps) == []


def test_bad_retrieval_low_score_and_empty():
    low = [mkstep("retrieval", "kb", input={"query": "q"}, output={"results": [{"score": 0.2}]})]
    assert types(detect_bad_retrieval(mkrun(), low)) == {taxonomy.BAD_RETRIEVAL}
    empty = [mkstep("retrieval", "kb", output={"results": []})]
    assert types(detect_bad_retrieval(mkrun(), empty)) == {taxonomy.BAD_RETRIEVAL}
    good = [mkstep("retrieval", "kb", output={"results": [{"score": 0.9}]})]
    assert detect_bad_retrieval(mkrun(), good) == []


def test_stale_memory_read_then_rewrite():
    steps = [
        mkstep("memory_read", "k", input={"key": "tier"}, output={"value": "old"}),
        mkstep("memory_write", "k", input={"key": "tier", "value": "new"}),
    ]
    assert types(detect_stale_memory(mkrun(), steps)) == {taxonomy.STALE_MEMORY}


def test_stale_memory_metadata_flag():
    steps = [
        mkstep("memory_read", "k", input={"key": "tier"}, output={"value": "old"},
               metadata={"stale": True})
    ]
    assert types(detect_stale_memory(mkrun(), steps)) == {taxonomy.STALE_MEMORY}


def test_context_pollution_from_bad_retrieval():
    steps = [
        mkstep("retrieval", "kb", output={"results": [{"score": 0.2, "text": "gift wrapping"}]}),
        mkstep("llm_call", "gpt", input={"messages": [{"content": "context: gift wrapping"}]}),
    ]
    assert types(detect_context_pollution(mkrun(), steps)) == {taxonomy.CONTEXT_POLLUTION}


def test_excessive_retry():
    steps = [mkstep("tool_call", "api.call", input={"i": i}) for i in range(3)]
    assert types(detect_excessive_retry(mkrun(), steps)) == {taxonomy.EXCESSIVE_RETRY}
    assert detect_excessive_retry(mkrun(), steps[:2]) == []


def test_loop_detected():
    steps = [mkstep("llm_call", "gpt", input={"q": "same"}) for _ in range(3)]
    assert types(detect_loop(mkrun(), steps)) == {taxonomy.LOOP_DETECTED}


def test_unsafe_write_action():
    unsafe = [mkstep("tool_call", "db.delete_record", input={"id": 1})]
    assert types(detect_unsafe_write_action(mkrun(), unsafe)) == {taxonomy.UNSAFE_WRITE_ACTION}
    # A preceding read makes it validated.
    safe = [
        mkstep("tool_call", "db.get_record", input={"id": 1}),
        mkstep("tool_call", "db.delete_record"),
    ]
    assert detect_unsafe_write_action(mkrun(), safe) == []


def test_permission_mismatch():
    steps = [mkstep("tool_call", "crm.delete")]
    run = mkrun(allowed_tools=["docs.read"])
    assert types(detect_permission_mismatch(run, steps)) == {taxonomy.PERMISSION_MISMATCH}
    # No allowed_tools declared -> detector is silent.
    assert detect_permission_mismatch(mkrun(), steps) == []


def test_final_answer_conflict():
    steps = [
        mkstep("tool_call", "order.refund", error="refund window expired"),
        mkstep("llm_call", "gpt",
               output={"role": "assistant", "content": "Refund was successful."}),
    ]
    assert types(detect_final_answer_conflict(mkrun(), steps)) == {taxonomy.FINAL_ANSWER_CONFLICT}
