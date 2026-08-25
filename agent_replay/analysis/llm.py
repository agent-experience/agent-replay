"""LLM-assisted detector interfaces (whitepaper §8.4).

These detectors delegate judgement to a language model instead of hard-coded heuristics.
They are *interfaces*: you inject a ``client`` — any callable ``(prompt: str) -> str`` —
so Agent Replay stays provider-agnostic and makes **no** network calls on its own. With no
client, a detector simply returns no findings.

Two are provided:

- :class:`LLMFailureClassifier` — classify a trace into taxonomy failure types.
- :class:`LLMRootCauseDetector` — name the single most likely root-cause failure.

Both are defensive: any client error or unparseable response yields ``[]`` rather than
raising, so analysis never breaks because of the model.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass

from ..schema import Run, Step
from . import taxonomy
from .models import Finding

# A client is any callable that maps a prompt to a completion string.
LLMClient = Callable[[str], str]


def _digest(run: Run, steps: list[Step], *, max_steps: int = 50) -> str:
    """Compact, model-friendly rendering of a run and its steps."""
    lines = [f"Run {run.run_id} agent={run.agent_name} status={run.status} task={run.task!r}"]
    for step in steps[:max_steps]:
        err = f" ERROR={step.error}" if step.error else ""
        lines.append(
            f"- {step.step_id} [{step.type}] name={step.name} "
            f"input={_short(step.input)} output={_short(step.output)}{err}"
        )
    return "\n".join(lines)


def _short(value: object, limit: int = 200) -> str:
    text = value if isinstance(value, str) else json.dumps(value, default=str)
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _extract_json(text: str):
    """Best-effort: pull the first JSON array or object out of a completion."""
    for opener, closer in (("[", "]"), ("{", "}")):
        start = text.find(opener)
        end = text.rfind(closer)
        if start != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                continue
    return None


@dataclass
class LLMDetector:
    """Base class for LLM-backed detectors. Subclasses implement :meth:`detect`."""

    client: LLMClient | None = None
    name: str = "llm"

    def __call__(self, run: Run, steps: list[Step]) -> list[Finding]:
        # Callable so it plugs into the same engine as deterministic detectors.
        return self.detect(run, steps)

    def detect(self, run: Run, steps: list[Step]) -> list[Finding]:  # pragma: no cover
        raise NotImplementedError

    def _ask(self, prompt: str) -> str | None:
        if self.client is None:
            return None
        try:
            return self.client(prompt)
        except Exception:
            return None


class LLMFailureClassifier(LLMDetector):
    """Ask the model to classify a trace into zero or more taxonomy failure types."""

    def __init__(self, client: LLMClient | None = None) -> None:
        super().__init__(client=client, name="llm_failure_classifier")

    def detect(self, run: Run, steps: list[Step]) -> list[Finding]:
        prompt = (
            "You are analyzing an AI agent run for failures. Choose zero or more failure "
            "types from this list:\n"
            + ", ".join(taxonomy.FAILURE_TYPES)
            + "\n\nReturn ONLY a JSON array of objects with keys: failure_type, step_id "
            "(or null), confidence (0-1), reason.\n\nTrace:\n"
            + _digest(run, steps)
        )
        raw = self._ask(prompt)
        if not raw:
            return []
        parsed = _extract_json(raw)
        if not isinstance(parsed, list):
            return []
        findings = []
        for item in parsed:
            if not isinstance(item, dict):
                continue
            ftype = item.get("failure_type")
            if ftype not in taxonomy.FAILURE_TYPES:
                continue
            findings.append(
                Finding(
                    failure_type=ftype,
                    detector=self.name,
                    message=str(item.get("reason") or taxonomy.DESCRIPTIONS[ftype]),
                    step_id=item.get("step_id"),
                    evidence={"source": "llm", "raw": item},
                    confidence=float(item.get("confidence", 0.5)),
                )
            )
        return findings


class LLMRootCauseDetector(LLMDetector):
    """Ask the model for the single most likely root-cause failure type."""

    def __init__(self, client: LLMClient | None = None) -> None:
        super().__init__(client=client, name="llm_root_cause")

    def detect(self, run: Run, steps: list[Step]) -> list[Finding]:
        prompt = (
            "You are diagnosing why an AI agent run failed. Identify the single most likely "
            "root cause. Choose one failure_type from:\n"
            + ", ".join(taxonomy.FAILURE_TYPES)
            + "\n\nReturn ONLY a JSON object with keys: failure_type, step_id (or null), "
            "confidence (0-1), root_cause (one sentence).\n\nTrace:\n"
            + _digest(run, steps)
        )
        raw = self._ask(prompt)
        if not raw:
            return []
        parsed = _extract_json(raw)
        if not isinstance(parsed, dict):
            return []
        ftype = parsed.get("failure_type")
        if ftype not in taxonomy.FAILURE_TYPES:
            return []
        return [
            Finding(
                failure_type=ftype,
                detector=self.name,
                message=str(parsed.get("root_cause") or taxonomy.DESCRIPTIONS[ftype]),
                step_id=parsed.get("step_id"),
                evidence={"source": "llm", "raw": parsed},
                confidence=float(parsed.get("confidence", 0.5)),
            )
        ]
