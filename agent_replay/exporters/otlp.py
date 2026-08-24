"""OpenTelemetry-compatible exporter (OTLP/JSON).

Agent Replay is not a replacement for OpenTelemetry — it builds on it. This exporter emits
a run as an OTLP ``TracesData`` JSON document so traces can flow into any OTLP-aware
backend, using the GenAI semantic conventions where they apply:

  Run  -> root span (span kind INTERNAL)
  Step -> child span, parented to the run span (or to ``parent_step_id``)

We build the JSON by hand so the core package has no ``opentelemetry-sdk`` dependency
(install the ``[otel]`` extra if you want to pipe through the real SDK). Trace/span ids are
derived deterministically from run/step ids so repeated exports are stable.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from datetime import datetime
from typing import Any

from ..schema import FAILED, LLM_CALL, RETRIEVAL, TOOL_CALL, Run, Step

# OTLP status codes: 0 UNSET, 1 OK, 2 ERROR. Span kinds: 1 INTERNAL.
_STATUS_OK = 1
_STATUS_ERROR = 2
_SPAN_KIND_INTERNAL = 1


def _hex(value: str, nbytes: int) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[: nbytes * 2]


def _ts_nanos(iso: str | None) -> int:
    if not iso:
        return 0
    dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    return int(dt.timestamp() * 1_000_000_000)


def _kv(key: str, value: Any) -> dict | None:
    """Build one OTLP KeyValue, or ``None`` to skip absent values."""
    if value is None:
        return None
    if isinstance(value, bool):
        av = {"boolValue": value}
    elif isinstance(value, int):
        av = {"intValue": str(value)}
    elif isinstance(value, float):
        av = {"doubleValue": value}
    elif isinstance(value, str):
        av = {"stringValue": value}
    else:
        av = {"stringValue": json.dumps(value, default=str)}
    return {"key": key, "value": av}


def _attrs(pairs: list[dict | None]) -> list[dict]:
    return [p for p in pairs if p is not None]


def _run_span(run: Run, trace_id: str) -> dict:
    start = _ts_nanos(run.started_at)
    end = _ts_nanos(run.ended_at) or start
    return {
        "traceId": trace_id,
        "spanId": _hex(run.run_id, 8),
        "name": run.agent_name,
        "kind": _SPAN_KIND_INTERNAL,
        "startTimeUnixNano": str(start),
        "endTimeUnixNano": str(end),
        "attributes": _attrs(
            [
                _kv("agent_replay.run_id", run.run_id),
                _kv("agent_replay.agent_name", run.agent_name),
                _kv("agent_replay.task", run.task),
                _kv("agent_replay.status", run.status),
                _kv("agent_replay.cost_usd", run.cost_usd),
                _kv("agent_replay.latency_ms", run.latency_ms),
            ]
        ),
        "status": {"code": _STATUS_ERROR if run.status == FAILED else _STATUS_OK},
    }


def _step_attributes(step: Step) -> list[dict]:
    pairs: list[dict | None] = [
        _kv("agent_replay.step_id", step.step_id),
        _kv("agent_replay.step_type", step.type),
    ]
    if step.type == LLM_CALL and isinstance(step.input, dict):
        pairs.append(_kv("gen_ai.system", step.input.get("provider")))
        pairs.append(_kv("gen_ai.request.model", step.input.get("model")))
        if isinstance(step.usage, dict):
            pairs.append(_kv("gen_ai.usage.input_tokens", step.usage.get("input_tokens")))
            pairs.append(_kv("gen_ai.usage.output_tokens", step.usage.get("output_tokens")))
    elif step.type == TOOL_CALL:
        pairs.append(_kv("gen_ai.tool.name", step.name))
    elif step.type == RETRIEVAL:
        pairs.append(_kv("gen_ai.tool.name", step.name))
        if isinstance(step.input, dict):
            pairs.append(_kv("agent_replay.retrieval.query", step.input.get("query")))
    if step.error:
        pairs.append(_kv("agent_replay.error", step.error))
    return _attrs(pairs)


def _step_span(step: Step, trace_id: str, run_span_id: str) -> dict:
    ts = _ts_nanos(step.timestamp)
    parent = _hex(step.parent_step_id, 8) if step.parent_step_id else run_span_id
    return {
        "traceId": trace_id,
        "spanId": _hex(f"{step.run_id}:{step.step_id}", 8),
        "parentSpanId": parent,
        "name": step.name or step.type,
        "kind": _SPAN_KIND_INTERNAL,
        "startTimeUnixNano": str(ts),
        "endTimeUnixNano": str(ts),
        "attributes": _step_attributes(step),
        "status": {"code": _STATUS_ERROR if step.error else _STATUS_OK},
    }


def export_run_otlp(run: Run, steps: Iterable[Step]) -> dict:
    """Return an OTLP/JSON ``TracesData`` dict for ``run`` and its ``steps``."""
    trace_id = _hex(run.run_id, 16)
    run_span = _run_span(run, trace_id)
    step_spans = [_step_span(s, trace_id, run_span["spanId"]) for s in steps]
    return {
        "resourceSpans": [
            {
                "resource": {
                    "attributes": _attrs(
                        [
                            _kv("service.name", run.agent_name),
                            _kv("telemetry.sdk.name", "agent-replay"),
                        ]
                    )
                },
                "scopeSpans": [
                    {
                        "scope": {"name": "agent-replay", "version": run.schema_version},
                        "spans": [run_span, *step_spans],
                    }
                ],
            }
        ]
    }
