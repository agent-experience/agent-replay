# Failure: ignored tool result

The `ticketing.update` tool returns `{"error": "ticket is locked ..."}`, but the agent's
final answer claims the ticket was closed successfully.

```bash
python examples/ignored_tool_result/main.py
agent-replay show latest
agent-replay analyze latest   # flags ignored_tool_result + final_answer_conflict
```

What to look for: the `tool_call` step shows an `error`, yet the subsequent `llm_call`
output asserts success. `agent-replay analyze` flags this as both `ignored_tool_result` and
`final_answer_conflict`, and points at the step to replay from.
