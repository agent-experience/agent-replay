"""Failure analysis + eval (Phase 2).

Public surface::

    from agent_replay.analysis import analyze, analyze_run, aggregate, register_detector

``analyze`` runs detectors over a recorded trace and returns an :class:`AnalysisReport`
(the eval shape from whitepaper §8.3). See :mod:`agent_replay.analysis.taxonomy` for the
built-in failure types and :mod:`agent_replay.analysis.detectors` for the detectors.
"""

from __future__ import annotations

from . import taxonomy
from .detectors import (
    builtin_detectors,
    clear_registry,
    register_detector,
    registered_detectors,
)
from .engine import aggregate, analyze, analyze_run
from .llm import LLMFailureClassifier, LLMRootCauseDetector
from .models import AnalysisReport, Finding

__all__ = [
    "analyze",
    "analyze_run",
    "aggregate",
    "register_detector",
    "registered_detectors",
    "clear_registry",
    "builtin_detectors",
    "AnalysisReport",
    "Finding",
    "LLMFailureClassifier",
    "LLMRootCauseDetector",
    "taxonomy",
]
