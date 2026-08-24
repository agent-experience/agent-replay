# Failure: ignored tool result

The `ticketing.update` tool returns `{"error": "ticket is locked ..."}`, but the agent's
final answer claims the ticket was closed successfully.

```bash
python examples/ignored_tool_result/main.py
agent-replay show latest
```

What to look for: the `tool_call` step shows an `error`, yet the subsequent `llm_call`
output asserts success — the `ignored_tool_result` failure mode (a `final_answer_conflict`
in the Phase 2 taxonomy).
