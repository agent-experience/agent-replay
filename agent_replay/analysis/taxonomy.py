"""Agent failure taxonomy (whitepaper §8.2).

The ten built-in failure types, each with a human-readable description and a default
severity. Detectors emit findings tagged with one of these types; the CLI and JSON export
use the descriptions and severities to build an explainable report.
"""

from __future__ import annotations

# Failure type constants.
HALLUCINATED_TOOL_ARGUMENT = "hallucinated_tool_argument"
IGNORED_TOOL_RESULT = "ignored_tool_result"
BAD_RETRIEVAL = "bad_retrieval"
STALE_MEMORY = "stale_memory"
CONTEXT_POLLUTION = "context_pollution"
EXCESSIVE_RETRY = "excessive_retry"
LOOP_DETECTED = "loop_detected"
UNSAFE_WRITE_ACTION = "unsafe_write_action"
PERMISSION_MISMATCH = "permission_mismatch"
FINAL_ANSWER_CONFLICT = "final_answer_conflict"

# Severity levels, ordered low -> high for aggregation.
LOW = "low"
MEDIUM = "medium"
HIGH = "high"
SEVERITY_ORDER = (LOW, MEDIUM, HIGH)

DESCRIPTIONS: dict[str, str] = {
    HALLUCINATED_TOOL_ARGUMENT: "Tool argument does not exist or does not match schema",
    IGNORED_TOOL_RESULT: "Tool returned an error, but the agent continued as if it succeeded",
    BAD_RETRIEVAL: "Retrieved content is poorly aligned with the task",
    STALE_MEMORY: "Old memory influenced the current decision incorrectly",
    CONTEXT_POLLUTION: "Context contains conflicting or irrelevant information",
    EXCESSIVE_RETRY: "Retry count is abnormally high",
    LOOP_DETECTED: "Agent repeats the same action pattern",
    UNSAFE_WRITE_ACTION: "Agent performs a write action without validation",
    PERMISSION_MISMATCH: "Agent attempts a tool call outside its permission scope",
    FINAL_ANSWER_CONFLICT: "Final answer conflicts with tool observations",
}

DEFAULT_SEVERITY: dict[str, str] = {
    HALLUCINATED_TOOL_ARGUMENT: HIGH,
    IGNORED_TOOL_RESULT: HIGH,
    BAD_RETRIEVAL: MEDIUM,
    STALE_MEMORY: MEDIUM,
    CONTEXT_POLLUTION: LOW,
    EXCESSIVE_RETRY: LOW,
    LOOP_DETECTED: MEDIUM,
    UNSAFE_WRITE_ACTION: HIGH,
    PERMISSION_MISMATCH: HIGH,
    FINAL_ANSWER_CONFLICT: HIGH,
}

# Every taxonomy type, in canonical order.
FAILURE_TYPES = tuple(DESCRIPTIONS.keys())


def severity_rank(severity: str) -> int:
    """Return a sortable rank for a severity string (unknown -> -1)."""
    try:
        return SEVERITY_ORDER.index(severity)
    except ValueError:
        return -1


def max_severity(severities: list[str]) -> str:
    """Return the highest severity in the list, or ``low`` if empty."""
    if not severities:
        return LOW
    return max(severities, key=severity_rank)
