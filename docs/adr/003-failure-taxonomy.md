# ADR 003: Failure Taxonomy

**Status:** Proposed (implemented in Phase 2; recorded now to shape Phase 1 examples)

## Context

Agent failure is a central problem, not an edge case: AgentBench and WebArena show that even
strong agents fail frequently on long-horizon and realistic tasks (see
[`../research.md`](../research.md)). A shared vocabulary of failure modes lets us build
detectors (Phase 2), suggest replay points (Phase 3), and extract guardrails (Phase 4).

## Decision

Adopt an initial taxonomy of failure types. Phase 1 ships runnable example traces for the
first three; Phase 2 will add deterministic and LLM-assisted detectors for the rest.

| Failure type | Description | Phase 1 example |
|---|---|---|
| `hallucinated_tool_argument` | Tool argument doesn't exist / mismatches schema | `examples/failed_tool_call` |
| `bad_retrieval` | Retrieved content poorly aligned with the task | `examples/bad_retrieval` |
| `ignored_tool_result` | Tool returned an error, agent continued as if it succeeded | `examples/ignored_tool_result` |
| `final_answer_conflict` | Final answer conflicts with tool observations | (Phase 2) |
| `stale_memory` | Old memory incorrectly influenced a decision | (Phase 2) |
| `context_pollution` | Conflicting/irrelevant context | (Phase 2) |
| `excessive_retry` | Abnormally high retry count | (Phase 2) |
| `loop_detected` | Agent repeats the same action pattern | (Phase 2) |
| `unsafe_write_action` | Write action without validation | (Phase 2) |
| `permission_mismatch` | Tool call outside permission scope | (Phase 2) |

## Consequences

- Phase 1 examples are chosen to demonstrate concrete, recognizable failure modes in the
  timeline, seeding the detector work in Phase 2.
- The taxonomy is a living document; new modes are added as real traces surface them.

## References

- AgentBench, WebArena — [`../research.md`](../research.md).
