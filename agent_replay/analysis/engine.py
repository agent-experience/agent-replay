"""Analysis engine: run detectors over a trace and build an :class:`AnalysisReport`.

``analyze`` runs the built-in detectors, any custom detectors registered via
:func:`~agent_replay.analysis.detectors.register_detector`, and any passed explicitly, then
aggregates their findings into the eval shape from whitepaper §8.3. ``aggregate`` rolls up
many reports into failure statistics (§8.4, "multiple runs can be aggregated").
"""

from __future__ import annotations

from collections import Counter

from ..schema import Run, Step
from ..store import Store
from . import taxonomy
from .detectors import Detector, builtin_detectors, registered_detectors
from .models import AnalysisReport, Finding


def analyze(
    run: Run,
    steps: list[Step],
    *,
    detectors: list[Detector] | None = None,
    extra_detectors: list[Detector] | None = None,
    include_registered: bool = True,
) -> AnalysisReport:
    """Analyze one run and return an :class:`AnalysisReport`.

    ``detectors`` replaces the built-in set entirely; otherwise built-ins are used. Custom
    registered detectors and ``extra_detectors`` are always appended.
    """
    dets: list[Detector] = list(detectors) if detectors is not None else builtin_detectors()
    if include_registered:
        dets += registered_detectors()
    if extra_detectors:
        dets += list(extra_detectors)

    findings: list[Finding] = []
    for det in dets:
        try:
            findings.extend(det(run, steps) or [])
        except Exception:
            # A misbehaving detector must never break analysis of the whole run.
            continue

    return _build_report(run, steps, findings)


def analyze_run(
    run_id: str,
    store: Store | None = None,
    **kwargs,
) -> AnalysisReport:
    """Load a run by id from the store and analyze it."""
    store = store or Store()
    run = store.get_run(run_id)
    if run is None:
        raise KeyError(f"run not found: {run_id}")
    steps = store.get_steps(run_id)
    return analyze(run, steps, **kwargs)


def _build_report(run: Run, steps: list[Step], findings: list[Finding]) -> AnalysisReport:
    # Preserve first-seen order of failure types.
    failure_types: list[str] = []
    for f in findings:
        if f.failure_type not in failure_types:
            failure_types.append(f.failure_type)

    severity = taxonomy.max_severity([f.severity for f in findings]) if findings else taxonomy.LOW
    confidence = round(max((f.confidence for f in findings), default=0.0), 4)

    # Suggested replay step: the earliest step (by trace order) any finding points at.
    index = {step.step_id: i for i, step in enumerate(steps)}
    flagged = [f.step_id for f in findings if f.step_id in index]
    suggested = min(flagged, key=lambda sid: index[sid]) if flagged else None

    # A run "succeeds" only if it was recorded successful *and* nothing was flagged.
    success = run.status == "success" and not findings

    return AnalysisReport(
        run_id=run.run_id,
        success=success,
        failure_types=failure_types,
        severity=severity,
        suggested_replay_step=suggested,
        confidence=confidence,
        findings=findings,
    )


def aggregate(reports: list[AnalysisReport]) -> dict:
    """Roll up many reports into failure statistics."""
    total = len(reports)
    successes = sum(1 for r in reports if r.success)
    type_counts: Counter = Counter()
    severity_counts: Counter = Counter()
    for r in reports:
        for ft in r.failure_types:
            type_counts[ft] += 1
        if r.findings:
            severity_counts[r.severity] += 1
    return {
        "total_runs": total,
        "successful_runs": successes,
        "failed_runs": total - successes,
        "success_rate": round(successes / total, 4) if total else 0.0,
        "failure_type_counts": dict(type_counts.most_common()),
        "severity_counts": dict(severity_counts),
    }
