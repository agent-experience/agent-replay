"""Tests for the LLM-assisted detector interfaces (injected fake client, no network)."""

from __future__ import annotations

from agent_replay.analysis import LLMFailureClassifier, LLMRootCauseDetector, taxonomy
from agent_replay.schema import Run, Step

RUN = Run(run_id="run_1", agent_name="a", status="failed")
STEPS = [Step(step_id="tool_call_1", run_id="run_1", type="tool_call", name="t", error="boom")]


def test_classifier_parses_json_array():
    def client(prompt: str) -> str:
        return (
            'Here is my analysis: [{"failure_type": "ignored_tool_result", '
            '"step_id": "tool_call_1", "confidence": 0.9, "reason": "ignored the error"}]'
        )

    findings = LLMFailureClassifier(client).detect(RUN, STEPS)
    assert len(findings) == 1
    assert findings[0].failure_type == taxonomy.IGNORED_TOOL_RESULT
    assert findings[0].confidence == 0.9
    assert findings[0].detector == "llm_failure_classifier"


def test_classifier_drops_unknown_types():
    def client(prompt: str) -> str:
        return '[{"failure_type": "not_a_real_type", "confidence": 0.9}]'

    assert LLMFailureClassifier(client).detect(RUN, STEPS) == []


def test_root_cause_parses_json_object():
    def client(prompt: str) -> str:
        return (
            '{"failure_type": "hallucinated_tool_argument", '
            '"confidence": 0.7, "root_cause": "bad field"}'
        )

    findings = LLMRootCauseDetector(client).detect(RUN, STEPS)
    assert len(findings) == 1
    assert findings[0].failure_type == taxonomy.HALLUCINATED_TOOL_ARGUMENT
    assert findings[0].message == "bad field"


def test_no_client_returns_nothing():
    assert LLMFailureClassifier().detect(RUN, STEPS) == []
    assert LLMRootCauseDetector().detect(RUN, STEPS) == []


def test_client_error_is_swallowed():
    def client(prompt: str) -> str:
        raise RuntimeError("api down")

    assert LLMFailureClassifier(client).detect(RUN, STEPS) == []


def test_unparseable_response_returns_nothing():
    assert LLMFailureClassifier(lambda p: "sorry, no JSON here").detect(RUN, STEPS) == []


def test_llm_detector_is_callable_like_a_detector():
    det = LLMRootCauseDetector(lambda p: '{"failure_type": "loop_detected", "confidence": 0.5}')
    # Usable directly as a detector callable (run, steps) -> findings.
    findings = det(RUN, STEPS)
    assert findings[0].failure_type == taxonomy.LOOP_DETECTED
