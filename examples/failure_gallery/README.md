# Failure gallery

Records one trace per failure type in the [taxonomy](../../docs/adr/003-failure-taxonomy.md)
(whitepaper §8.2), each crafted so its matching detector fires. Use it to see every kind of
report Agent Replay can produce.

```bash
python examples/failure_gallery/main.py
agent-replay stats            # failure statistics across all 10 runs
agent-replay analyze latest   # explainable report for the most recent run
```

Each run is tagged with `failure_type` metadata. Detectors are heuristic and independent, so
a single run may surface more than one signal (e.g. a run that ignores a tool error also
tends to show a `final_answer_conflict`).

For more realistic, single-failure walkthroughs see the standalone examples:
[`failed_tool_call`](../failed_tool_call/), [`bad_retrieval`](../bad_retrieval/), and
[`ignored_tool_result`](../ignored_tool_result/).
