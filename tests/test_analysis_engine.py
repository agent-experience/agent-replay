"""Tests for the analysis engine: aggregation, custom detectors, report shape."""

from __future__ import annotations

import pytest

from agent_replay.analysis import (
    Finding,
    aggregate,
    analyze,
    clear_registry,
    register_detector,
    taxonomy,
)
from agent_replay.schema import Run, Step


def mkrun(status: str = "failed", **metadata) -> Run:
    return Run(run_id="run_1", agent_name="a", status=status, metadata=metadata)


def steps_with_two_failures():
    return [
        Step(step_id="tool_call_1", run_id="run_1", type="tool_call", name="crm.update",
             input={"refund_status": "x"}, error="field refund_status is deprecated"),
        Step(step_id="llm_call_2", run_id="run_1", type="llm_call", name="gpt",
             output={"role": "assistant", "content": "All done successfully."}),
    ]


def test_report_shape_and_aggregation():
    report = analyze(mkrun(), steps_with_two_failures())
    assert report.run_id == "run_1"
    assert report.success is False
    assert taxonomy.HALLUCINATED_TOOL_ARGUMENT in report.failure_types
    assert report.severity == taxonomy.HIGH
    assert 0 < report.confidence <= 1
    # Suggested replay = earliest flagged step in trace order.
    assert report.suggested_replay_step == "tool_call_1"
    d = report.to_dict()
    assert set(d) >= {
        "run_id", "success", "failure_types", "severity",
        "suggested_replay_step", "confidence", "findings",
    }


def test_clean_run_is_success():
    steps = [Step(step_id="llm_call_1", run_id="run_1", type="llm_call", name="gpt",
                  output={"role": "assistant", "content": "here you go"})]
    report = analyze(mkrun(status="success"), steps)
    assert report.success is True
    assert report.failure_types == []
    assert report.suggested_replay_step is None


def test_detector_exception_does_not_break_analysis():
    def boom(run, steps):
        raise RuntimeError("bad detector")

    report = analyze(mkrun(status="success"), [], extra_detectors=[boom])
    assert report.success is True  # analysis survived the crashing detector


def test_custom_registered_detector():
    def always(run, steps):
        return [Finding(failure_type=taxonomy.LOOP_DETECTED, detector="custom", message="hi")]

    register_detector("custom_always", always)
    try:
        report = analyze(mkrun(status="success"), [])
        assert taxonomy.LOOP_DETECTED in report.failure_types
    finally:
        clear_registry()


def test_aggregate_over_runs():
    r1 = analyze(mkrun(), steps_with_two_failures())
    r2 = analyze(mkrun(status="success"), [])
    agg = aggregate([r1, r2])
    assert agg["total_runs"] == 2
    assert agg["successful_runs"] == 1
    assert agg["failed_runs"] == 1
    assert agg["success_rate"] == 0.5
    assert taxonomy.HALLUCINATED_TOOL_ARGUMENT in agg["failure_type_counts"]


@pytest.fixture(autouse=True)
def _clean_registry():
    clear_registry()
    yield
    clear_registry()
