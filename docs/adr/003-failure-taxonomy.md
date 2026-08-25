# ADR 003: Failure Taxonomy

**Status:** Accepted (implemented in Phase 2)

## Context

Agent failure is a central problem, not an edge case: AgentBench and WebArena show that even
strong agents fail frequently on long-horizon and realistic tasks (see
[`../research.md`](../research.md)). A shared vocabulary of failure modes lets us build
detectors (Phase 2), suggest replay points (Phase 3), and extract guardrails (Phase 4).

## Decision

Adopt an initial taxonomy of failure types. Each has a deterministic detector
(`agent_replay/analysis/detectors.py`) and a runnable example trace. The three most common
modes also have dedicated, more realistic standalone examples.

| Failure type | Description | Example trace |
|---|---|---|
| `hallucinated_tool_argument` | Tool argument doesn't exist / mismatches schema | `examples/failed_tool_call` |
| `bad_retrieval` | Retrieved content poorly aligned with the task | `examples/bad_retrieval` |
| `ignored_tool_result` | Tool returned an error, agent continued as if it succeeded | `examples/ignored_tool_result` |
| `final_answer_conflict` | Final answer conflicts with tool observations | `examples/failure_gallery` |
| `stale_memory` | Old memory incorrectly influenced a decision | `examples/failure_gallery` |
| `context_pollution` | Conflicting/irrelevant context | `examples/failure_gallery` |
| `excessive_retry` | Abnormally high retry count | `examples/failure_gallery` |
| `loop_detected` | Agent repeats the same action pattern | `examples/failure_gallery` |
| `unsafe_write_action` | Write action without validation | `examples/failure_gallery` |
| `permission_mismatch` | Tool call outside permission scope | `examples/failure_gallery` |

Detectors are **heuristic**: they surface signals for a developer to confirm, are independent
(a run may match several), and severity/confidence are advisory. Two LLM-assisted detector
interfaces (`LLMFailureClassifier`, `LLMRootCauseDetector`) let a caller delegate judgement to
a model without Agent Replay making any network calls itself.

## Consequences

- A shared, versioned vocabulary lets `analyze` produce explainable reports, `stats` aggregate
  across runs, and Phase 3/4 suggest replay points and extract guardrails.
- The taxonomy is a living document; new modes are added as real traces surface them.
- Because detectors overlap by design, reports rank findings and the engine picks the earliest
  flagged step as the suggested replay point.

## References

- AgentBench, WebArena — [`../research.md`](../research.md).
