# Failure: hallucinated tool argument

The agent calls `crm.update_customer` with `refund_status`, a field that isn't in the CRM
schema. The tool returns `{"error": "field refund_status is deprecated"}`.

```bash
python examples/failed_tool_call/main.py
agent-replay show latest
```

What to look for: the `tool_call` step's `input` contains `refund_status`, and its `error`
line (shown in red) reveals the schema mismatch. This is the `hallucinated_tool_argument`
failure mode that the Phase 2 `analyze` command will detect automatically.
