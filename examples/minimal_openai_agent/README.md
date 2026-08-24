# Minimal agent (happy path)

The smallest end-to-end trace: a mock LLM decides to call a search tool, the tool returns a
result, and the LLM produces a final answer. No API keys required.

```bash
python examples/minimal_openai_agent/main.py
agent-replay show latest
```

What to look for in the timeline: two `llm_call` steps around a single `tool_call`, each with
its input/output and token usage.
