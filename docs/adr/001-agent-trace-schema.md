# ADR 001: Agent Trace Schema

**Status:** Accepted (Phase 1)

## Context

An agent run is a *trajectory*, not a single request/response (see ReAct in
[`../research.md`](../research.md)). To debug and later replay it, we need a structured,
versioned record of what happened at each step.

## Decision

Model a trace as two record types:

- **`Run`** — one complete execution of an agent task: `run_id`, `agent_name`, `task`,
  `started_at`/`ended_at`, `status` (`running`/`success`/`failed`), `cost_usd`, `latency_ms`,
  `metadata`, `schema_version`.
- **`Step`** — one meaningful state transition: `step_id`, `run_id`, `type`, `name`,
  `input`, `output`, `state_before`, `state_after`, `error`, `usage`, `parent_step_id`,
  `timestamp`, `metadata`.

Phase 1 step `type`s: `llm_call`, `tool_call`, `retrieval`, `memory_read`, `memory_write`.

Design choices:

- Plain `dataclasses` (no Pydantic) to keep the SDK dependency-light.
- A module-level `SCHEMA_VERSION` string so exported traces are self-describing.
- `from_dict` preserves unknown top-level keys under `metadata`, so the schema can grow
  without breaking older readers (extensibility).
- Step ids follow `<type>_<n>` where `n` is the 1-based step index within the run
  (e.g. `tool_call_4`), matching the whitepaper §5.2 example.

## Consequences

- The schema round-trips cleanly through JSON and SQLite.
- Adding a new step type or field is backward-compatible.
- Implemented in [`../../agent_replay/schema.py`](../../agent_replay/schema.py).

## References

- ReAct (reasoning + acting trajectories) — [`../research.md`](../research.md).
