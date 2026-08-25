"""Deterministic failure detectors + the detector registry.

A **detector** is any callable ``(run, steps) -> list[Finding]``. Ten built-in detectors
cover the whitepaper §8.2 taxonomy. Users can add their own with :func:`register_detector`;
the engine runs built-ins, registered detectors, and any passed explicitly.

Detectors are heuristic by design — they surface *signals* for a developer to confirm, not
proofs. Each is deliberately conservative and self-contained so it can be unit-tested against
a single crafted trace.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from collections.abc import Callable

from ..schema import LLM_CALL, MEMORY_READ, MEMORY_WRITE, RETRIEVAL, TOOL_CALL, Run, Step
from . import taxonomy
from .models import Finding

Detector = Callable[[Run, list[Step]], list[Finding]]

# ---------------------------------------------------------------------------
# Registry (custom, user-defined detectors — whitepaper §8.4)
# ---------------------------------------------------------------------------
_REGISTRY: dict[str, Detector] = {}


def register_detector(name: str, fn: Detector | None = None):
    """Register a custom detector, as a call or a decorator.

    Direct::

        register_detector("my_check", my_check)

    Decorator::

        @register_detector("my_check")
        def my_check(run, steps): ...
    """
    if fn is not None:
        _REGISTRY[name] = fn
        return fn

    def _decorator(f: Detector) -> Detector:
        _REGISTRY[name] = f
        return f

    return _decorator


def registered_detectors() -> list[Detector]:
    """Return all custom detectors registered via :func:`register_detector`."""
    return list(_REGISTRY.values())


def clear_registry() -> None:
    """Remove all registered custom detectors (mostly for tests)."""
    _REGISTRY.clear()


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------
def _text(value: object) -> str:
    """Lowercased, JSON-flattened text of any value — for keyword scanning."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value.lower()
    return json.dumps(value, default=str).lower()


def _error_text(step: Step) -> str | None:
    """Return the step's error, whether on ``step.error`` or inside its output dict."""
    if step.error:
        return str(step.error)
    if isinstance(step.output, dict) and step.output.get("error"):
        return str(step.output["error"])
    return None


def _content(message: object) -> str:
    """Extract assistant text content from an llm output_message-shaped value."""
    if isinstance(message, dict):
        return _text(message.get("content"))
    return _text(message)


_SUCCESS_WORDS = re.compile(
    r"\b(done|success(ful|fully)?|completed?|closed?|approved?|resolved?|fixed)\b"
)


def _claims_success(step: Step) -> bool:
    return bool(_SUCCESS_WORDS.search(_content(step.output)))


def _retrieval_scores(step: Step) -> list[float]:
    results = step.output.get("results") if isinstance(step.output, dict) else None
    scores: list[float] = []
    if isinstance(results, list):
        for item in results:
            if isinstance(item, dict) and isinstance(item.get("score"), (int, float)):
                scores.append(float(item["score"]))
    return scores


# Thresholds (module-level so tests / users can tune them).
BAD_RETRIEVAL_MIN_SCORE = 0.5
EXCESSIVE_RETRY_THRESHOLD = 3  # same tool name called this many times or more
LOOP_REPEAT_THRESHOLD = 3  # identical (type, name, input) signature this many times or more

_SCHEMA_MISMATCH = re.compile(
    r"deprecated|unknown (field|argument|parameter|key)|no such (field|column)|"
    r"unexpected keyword|not a valid|does not exist|unrecognized|invalid (field|argument)"
)

# Only destructive writes are treated as "unsafe" by default — flagging every update/create
# would fire on most healthy runs. Non-destructive writes can opt in via metadata write=True.
_DESTRUCTIVE_VERB = re.compile(r"(^|[._])(delete|drop|remove|purge|truncate|wipe|destroy)")
_READ_VERB = re.compile(
    r"(^|[._])(get|list|read|search|fetch|lookup|validate|check|find|query|describe)"
)


# ---------------------------------------------------------------------------
# Detectors
# ---------------------------------------------------------------------------
def detect_hallucinated_tool_argument(run: Run, steps: list[Step]) -> list[Finding]:
    findings = []
    for step in steps:
        if step.type != TOOL_CALL:
            continue
        err = _error_text(step)
        if err and _SCHEMA_MISMATCH.search(err.lower()):
            findings.append(
                Finding(
                    failure_type=taxonomy.HALLUCINATED_TOOL_ARGUMENT,
                    detector="hallucinated_tool_argument",
                    message=f"Tool '{step.name}' argument was rejected by the schema: {err}",
                    step_id=step.step_id,
                    evidence={"tool": step.name, "arguments": step.input, "error": err},
                    confidence=0.8,
                )
            )
    return findings


def detect_ignored_tool_result(run: Run, steps: list[Step]) -> list[Finding]:
    findings = []
    for i, step in enumerate(steps):
        if step.type != TOOL_CALL or not _error_text(step):
            continue
        later = steps[i + 1 :]
        # Was the same tool retried and did it succeed afterward?
        recovered = any(
            s.type == TOOL_CALL and s.name == step.name and not _error_text(s) for s in later
        )
        if recovered:
            continue
        # Did the agent keep going (another step) and end up claiming success?
        continued = bool(later)
        claimed_success = run.status == "success" or any(
            s.type == LLM_CALL and _claims_success(s) for s in later
        )
        if continued and claimed_success:
            findings.append(
                Finding(
                    failure_type=taxonomy.IGNORED_TOOL_RESULT,
                    detector="ignored_tool_result",
                    message=(
                        f"Tool '{step.name}' returned an error but the agent continued and "
                        f"treated the run as successful."
                    ),
                    step_id=step.step_id,
                    evidence={"tool": step.name, "error": _error_text(step)},
                    confidence=0.7,
                )
            )
    return findings


def detect_bad_retrieval(run: Run, steps: list[Step]) -> list[Finding]:
    findings = []
    for step in steps:
        if step.type != RETRIEVAL:
            continue
        scores = _retrieval_scores(step)
        results = step.output.get("results") if isinstance(step.output, dict) else None
        if isinstance(results, list) and len(results) == 0:
            findings.append(
                Finding(
                    failure_type=taxonomy.BAD_RETRIEVAL,
                    detector="bad_retrieval",
                    message=f"Retrieval '{step.name}' returned no results.",
                    step_id=step.step_id,
                    evidence={"query": step.input, "results": 0},
                    confidence=0.7,
                )
            )
        elif scores and max(scores) < BAD_RETRIEVAL_MIN_SCORE:
            findings.append(
                Finding(
                    failure_type=taxonomy.BAD_RETRIEVAL,
                    detector="bad_retrieval",
                    message=(
                        f"Retrieval '{step.name}' returned only low-relevance results "
                        f"(top score {max(scores):.2f} < {BAD_RETRIEVAL_MIN_SCORE})."
                    ),
                    step_id=step.step_id,
                    evidence={"query": step.input, "top_score": max(scores), "scores": scores},
                    confidence=0.65,
                )
            )
    return findings


def detect_stale_memory(run: Run, steps: list[Step]) -> list[Finding]:
    findings = []
    for i, step in enumerate(steps):
        if step.type != MEMORY_READ:
            continue
        key = step.input.get("key") if isinstance(step.input, dict) else None
        read_value = step.output.get("value") if isinstance(step.output, dict) else None
        # Explicit signal: the read is flagged stale in metadata.
        if step.metadata.get("stale"):
            findings.append(
                Finding(
                    failure_type=taxonomy.STALE_MEMORY,
                    detector="stale_memory",
                    message=f"Memory read of '{key}' is flagged stale.",
                    step_id=step.step_id,
                    evidence={"key": key, "value": read_value},
                    confidence=0.7,
                )
            )
            continue
        # Inferred signal: the same key is written a *different* value later in the run,
        # which means the value read here was out of date.
        for later in steps[i + 1 :]:
            if later.type != MEMORY_WRITE:
                continue
            later_key = later.input.get("key") if isinstance(later.input, dict) else None
            later_value = later.input.get("value") if isinstance(later.input, dict) else None
            if later_key == key and later_value != read_value:
                findings.append(
                    Finding(
                        failure_type=taxonomy.STALE_MEMORY,
                        detector="stale_memory",
                        message=(
                            f"Memory key '{key}' was read then rewritten with a different value; "
                            f"the earlier read was stale."
                        ),
                        step_id=step.step_id,
                        evidence={"key": key, "read": read_value, "later_write": later_value},
                        confidence=0.6,
                    )
                )
                break
    return findings


def detect_context_pollution(run: Run, steps: list[Step]) -> list[Finding]:
    """Flag an llm_call whose context includes text from a low-relevance retrieval."""
    findings = []
    # Collect identifying snippets from bad retrievals earlier in the run.
    bad_snippets: list[tuple[str, str]] = []  # (retrieval step_id, snippet text)
    for step in steps:
        if step.type != RETRIEVAL:
            continue
        scores = _retrieval_scores(step)
        if not (scores and max(scores) < BAD_RETRIEVAL_MIN_SCORE):
            continue
        results = step.output.get("results") if isinstance(step.output, dict) else []
        for item in results if isinstance(results, list) else []:
            if isinstance(item, dict):
                snippet = str(item.get("text") or item.get("id") or "").lower()
                if snippet:
                    bad_snippets.append((step.step_id, snippet))

    if not bad_snippets:
        return findings

    for step in steps:
        if step.type != LLM_CALL:
            continue
        haystack = _text(step.input)
        for src_step, snippet in bad_snippets:
            if snippet and snippet in haystack:
                findings.append(
                    Finding(
                        failure_type=taxonomy.CONTEXT_POLLUTION,
                        detector="context_pollution",
                        message=(
                            "LLM context includes low-relevance retrieved content "
                            f"(from {src_step}), which can pollute the decision."
                        ),
                        step_id=step.step_id,
                        evidence={"llm_step": step.step_id, "source_retrieval": src_step},
                        confidence=0.5,
                    )
                )
                break
    return findings


def detect_excessive_retry(run: Run, steps: list[Step]) -> list[Finding]:
    counts = Counter(s.name for s in steps if s.type == TOOL_CALL and s.name)
    threshold = EXCESSIVE_RETRY_THRESHOLD
    findings = []
    for name, count in counts.items():
        if count >= threshold:
            first = next(s for s in steps if s.type == TOOL_CALL and s.name == name)
            findings.append(
                Finding(
                    failure_type=taxonomy.EXCESSIVE_RETRY,
                    detector="excessive_retry",
                    message=f"Tool '{name}' was called {count} times (threshold {threshold}).",
                    step_id=first.step_id,
                    evidence={"tool": name, "count": count},
                    confidence=0.7,
                )
            )
    return findings


def detect_loop(run: Run, steps: list[Step]) -> list[Finding]:
    signatures: dict[tuple, Step] = {}
    counts: Counter = Counter()
    for step in steps:
        sig = (step.type, step.name, _text(step.input))
        counts[sig] += 1
        signatures.setdefault(sig, step)
    findings = []
    for sig, count in counts.items():
        if count >= LOOP_REPEAT_THRESHOLD:
            step = signatures[sig]
            findings.append(
                Finding(
                    failure_type=taxonomy.LOOP_DETECTED,
                    detector="loop_detected",
                    message=(
                        f"Action '{step.type}:{step.name}' with identical input repeated "
                        f"{count} times."
                    ),
                    step_id=step.step_id,
                    evidence={"type": step.type, "name": step.name, "count": count},
                    confidence=0.7,
                )
            )
    return findings


def detect_unsafe_write_action(run: Run, steps: list[Step]) -> list[Finding]:
    """Flag a *destructive* (or metadata-flagged) write that ran with no preceding validation.

    Only destructive verbs (delete/drop/remove/…) fire by default — routine creates/updates
    are far too common to treat as failures. A non-destructive tool can still opt in via
    ``metadata={"write": True}``.
    """
    findings = []
    seen_validation = False
    for step in steps:
        if step.type in (RETRIEVAL, MEMORY_READ):
            seen_validation = True
        if step.type == TOOL_CALL and step.name:
            name = step.name.lower()
            is_write = bool(_DESTRUCTIVE_VERB.search(name)) or bool(step.metadata.get("write"))
            is_read = bool(_READ_VERB.search(name))
            if is_read:
                seen_validation = True
            if is_write and not seen_validation and not step.metadata.get("validated"):
                findings.append(
                    Finding(
                        failure_type=taxonomy.UNSAFE_WRITE_ACTION,
                        detector="unsafe_write_action",
                        message=(
                            f"Destructive tool '{step.name}' ran with no preceding validation "
                            f"(read/retrieval/check)."
                        ),
                        step_id=step.step_id,
                        evidence={"tool": step.name},
                        confidence=0.6,
                    )
                )
    return findings


def detect_permission_mismatch(run: Run, steps: list[Step]) -> list[Finding]:
    allowed = run.metadata.get("allowed_tools") or run.metadata.get("permissions")
    if not isinstance(allowed, (list, tuple, set)):
        return []
    allowed_set = set(allowed)
    findings = []
    for step in steps:
        if step.type == TOOL_CALL and step.name and step.name not in allowed_set:
            findings.append(
                Finding(
                    failure_type=taxonomy.PERMISSION_MISMATCH,
                    detector="permission_mismatch",
                    message=(
                        f"Tool '{step.name}' is outside the agent's allowed scope "
                        f"{sorted(allowed_set)}."
                    ),
                    step_id=step.step_id,
                    evidence={"tool": step.name, "allowed_tools": sorted(allowed_set)},
                    confidence=0.85,
                )
            )
    return findings


def detect_final_answer_conflict(run: Run, steps: list[Step]) -> list[Finding]:
    llm_steps = [s for s in steps if s.type == LLM_CALL]
    if not llm_steps:
        return []
    final = llm_steps[-1]
    if not _claims_success(final):
        return []
    final_index = steps.index(final)
    for step in steps[:final_index]:
        if step.type == TOOL_CALL and _error_text(step):
            return [
                Finding(
                    failure_type=taxonomy.FINAL_ANSWER_CONFLICT,
                    detector="final_answer_conflict",
                    message=(
                        "Final answer claims success, but an earlier tool observation was an "
                        f"error (from {step.step_id})."
                    ),
                    step_id=final.step_id,
                    evidence={
                        "final_step": final.step_id,
                        "conflicting_step": step.step_id,
                        "error": _error_text(step),
                    },
                    confidence=0.7,
                )
            ]
    return []


def builtin_detectors() -> list[Detector]:
    """The ten deterministic detectors covering the §8.2 taxonomy."""
    return [
        detect_hallucinated_tool_argument,
        detect_ignored_tool_result,
        detect_bad_retrieval,
        detect_stale_memory,
        detect_context_pollution,
        detect_excessive_retry,
        detect_loop,
        detect_unsafe_write_action,
        detect_permission_mismatch,
        detect_final_answer_conflict,
    ]
