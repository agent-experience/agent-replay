"""Active-trace context.

A :class:`~contextvars.ContextVar` holds a *stack* of :class:`TraceFrame` objects so
that ``trace()`` blocks can nest (technical acceptance criterion "SDK supports nested
trace context"). ``event.*`` recorders attach to the innermost frame.

The stack is stored immutably (each push/pop replaces the list) so it plays well with
``contextvars`` copy-on-fork semantics across threads and async tasks. Frame *objects*
are shared by reference, so mutating ``frame.step_count`` is visible to the enclosing
``trace()``.
"""

from __future__ import annotations

import contextvars
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # avoid import cycles at runtime
    from .redaction import RedactionConfig
    from .schema import Run
    from .store import Store

_stack: contextvars.ContextVar = contextvars.ContextVar("agent_replay_stack", default=())


@dataclass
class TraceFrame:
    """One active ``trace()`` block."""

    run: Run
    store: Store
    redaction: RedactionConfig
    step_count: int = field(default=0)


def push_frame(frame: TraceFrame) -> None:
    _stack.set((*_stack.get(), frame))


def pop_frame() -> TraceFrame | None:
    stack = _stack.get()
    if not stack:
        return None
    _stack.set(stack[:-1])
    return stack[-1]


def current_frame() -> TraceFrame | None:
    stack = _stack.get()
    return stack[-1] if stack else None


def depth() -> int:
    return len(_stack.get())
