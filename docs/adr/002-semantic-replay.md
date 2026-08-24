# ADR 002: Semantic Replay (not OS-level deterministic replay)

**Status:** Accepted (Phase 1 defines the model; Phases 2–3 extend it)

## Context

The systems community has a mature record/replay tradition — **rr**, **CRIU**, and microVM
snapshot/restore (**Firecracker**) — that can reproduce executions deterministically at the
OS level (see [`../research.md`](../research.md)). That is powerful but heavy, brittle across
environments, and mismatched to what agent developers actually debug: *semantic* decisions
(prompts, tool arguments, retrieved context, memory state), not CPU instructions.

## Decision

Agent Replay implements **semantic replay**, defined in three modes:

| Mode | Meaning | Phase |
|---|---|---|
| **Playback** | Re-emit the recorded trajectory without calling models or tools | 1 |
| **Mocked** | Freeze selected LLM/tool/retrieval outputs and rerun downstream logic | 2 |
| **Forked** | Change prompt/model/tool/retriever/memory config from a step onward | 3 |

Phase 1 promises **playback only**. To make later modes safe:

- Every step records `input`, `output`, `state_before`, and `state_after`.
- **Side-effectful tools are never automatically re-executed.** Read-only tools may be, and
  external outputs may be mocked — but only under explicit developer control.

## Consequences

- Clear, honest replay semantics: v0 does not claim byte-level determinism.
- `PlaybackReplay` (see [`../../agent_replay/replay.py`](../../agent_replay/replay.py)) never
  performs external I/O; `verify()` asserts playback equals the stored trace.
- The recorded `state_before`/`state_after` fields are the seam that Phase 2 (mocked) and
  Phase 3 (forked) replay build on.

## References

- rr, CRIU, Firecracker — [`../research.md`](../research.md).
