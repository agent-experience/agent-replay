"""Event recorders — the manual instrumentation API.

Each function records one :class:`~agent_replay.schema.Step` against the innermost active
``trace()``. Calling a recorder outside a ``trace()`` is a no-op (with a warning) so that
instrumentation can never crash the host agent.

Step ids follow the whitepaper convention ``<type>_<n>`` where ``n`` is the 1-based step
index within the run (e.g. the 4th step, if it is a tool call, is ``tool_call_4``).
"""

from __future__ import annotations

import warnings
from typing import Any

from . import context
from .schema import (
    LLM_CALL,
    MEMORY_READ,
    MEMORY_WRITE,
    RETRIEVAL,
    TOOL_CALL,
    Step,
    utc_now_iso,
)


def _record(
    step_type: str,
    *,
    name: str | None = None,
    input: Any = None,
    output: Any = None,
    state_before: Any = None,
    state_after: Any = None,
    error: str | None = None,
    usage: dict | None = None,
    parent_step_id: str | None = None,
    metadata: dict | None = None,
) -> Step | None:
    frame = context.current_frame()
    if frame is None:
        warnings.warn(
            f"agent_replay: event.{step_type} called outside an active trace(); ignored",
            stacklevel=3,
        )
        return None

    frame.step_count += 1
    fields = frame.redaction.apply(
        {
            "input": input,
            "output": output,
            "state_before": state_before,
            "state_after": state_after,
        }
    )
    step = Step(
        step_id=f"{step_type}_{frame.step_count}",
        run_id=frame.run.run_id,
        type=step_type,
        name=name,
        input=fields.get("input"),
        output=fields.get("output"),
        state_before=fields.get("state_before"),
        state_after=fields.get("state_after"),
        error=error,
        usage=usage,
        parent_step_id=parent_step_id,
        timestamp=utc_now_iso(),
        metadata=metadata or {},
    )
    frame.store.insert_step(step)
    return step


def llm_call(
    provider: str,
    model: str,
    input_messages: Any = None,
    output_message: Any = None,
    usage: dict | None = None,
    name: str | None = None,
    error: str | None = None,
    **metadata,
) -> Step | None:
    """Record a model call."""
    return _record(
        LLM_CALL,
        name=name or model,
        input={"provider": provider, "model": model, "messages": input_messages},
        output=output_message,
        usage=usage,
        error=error,
        metadata=metadata,
    )


def tool_call(
    name: str,
    input: Any = None,
    output: Any = None,
    error: str | None = None,
    state_before: Any = None,
    state_after: Any = None,
    **metadata,
) -> Step | None:
    """Record a tool invocation."""
    return _record(
        TOOL_CALL,
        name=name,
        input=input,
        output=output,
        error=error,
        state_before=state_before,
        state_after=state_after,
        metadata=metadata,
    )


def retrieval(
    name: str,
    query: Any = None,
    results: Any = None,
    error: str | None = None,
    **metadata,
) -> Step | None:
    """Record a retrieval / search event."""
    return _record(
        RETRIEVAL,
        name=name,
        input={"query": query},
        output={"results": results},
        error=error,
        metadata=metadata,
    )


def memory_read(
    key: str | None = None,
    value: Any = None,
    name: str | None = None,
    **metadata,
) -> Step | None:
    """Record a memory read."""
    return _record(
        MEMORY_READ,
        name=name or key,
        input={"key": key},
        output={"value": value},
        metadata=metadata,
    )


def memory_write(
    key: str | None = None,
    value: Any = None,
    name: str | None = None,
    **metadata,
) -> Step | None:
    """Record a memory write."""
    return _record(
        MEMORY_WRITE,
        name=name or key,
        input={"key": key, "value": value},
        metadata=metadata,
    )


def step(step_type: str, name: str | None = None, **kwargs) -> Step | None:
    """Low-level escape hatch to record an arbitrary step type."""
    return _record(step_type, name=name, **kwargs)
