"""Analysis result types: :class:`Finding` and :class:`AnalysisReport`.

A :class:`Finding` is one piece of evidence emitted by a detector. An :class:`AnalysisReport`
aggregates the findings for a run into the eval shape from whitepaper §8.3.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from . import taxonomy


@dataclass
class Finding:
    """One detected failure signal within a run."""

    failure_type: str
    detector: str
    message: str
    step_id: str | None = None
    evidence: dict = field(default_factory=dict)
    confidence: float = 0.5
    severity: str | None = None

    def __post_init__(self) -> None:
        # Fall back to the taxonomy default severity when a detector doesn't set one.
        if self.severity is None:
            self.severity = taxonomy.DEFAULT_SEVERITY.get(self.failure_type, taxonomy.MEDIUM)

    def to_dict(self) -> dict:
        return {
            "failure_type": self.failure_type,
            "detector": self.detector,
            "message": self.message,
            "step_id": self.step_id,
            "evidence": self.evidence,
            "confidence": self.confidence,
            "severity": self.severity,
        }


@dataclass
class AnalysisReport:
    """The result of analyzing one run (whitepaper §8.3)."""

    run_id: str
    success: bool
    failure_types: list[str]
    severity: str
    suggested_replay_step: str | None
    confidence: float
    findings: list[Finding] = field(default_factory=list)

    def to_dict(self, *, include_findings: bool = True) -> dict[str, Any]:
        out: dict[str, Any] = {
            "run_id": self.run_id,
            "success": self.success,
            "failure_types": self.failure_types,
            "severity": self.severity,
            "suggested_replay_step": self.suggested_replay_step,
            "confidence": self.confidence,
        }
        if include_findings:
            out["findings"] = [f.to_dict() for f in self.findings]
        return out
