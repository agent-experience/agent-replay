# Python SDK Reference

## Tracing

### `trace(agent_name, task, **kwargs)`

Context manager that records an agent run.

```python
from agent_replay import trace

with trace("my-agent", task="Summarize report") as run:
    # record events here
    pass
```

**Parameters:**
- `agent_name` (str) — Name of the agent
- `task` (str) — Description of the task
- `redact` (callable, optional) — Function to scrub data before storage
- `metadata` (dict, optional) — Arbitrary metadata attached to the run

Also works as a decorator:

```python
@trace("my-agent")
def run_agent(task):
    ...
```

## Events

### `event.llm_call(**kwargs)`

Record a language model call.

```python
from agent_replay import event

event.llm_call(
    provider="openai",
    model="gpt-5.5",
    input_messages=[{"role": "user", "content": "Hello"}],
    output_message={"role": "assistant", "content": "Hi there"},
    usage={"input_tokens": 10, "output_tokens": 5},
)
```

### `event.tool_call(**kwargs)`

Record a tool invocation.

```python
event.tool_call(
    name="search",
    input={"query": "pricing"},
    output={"results": [...]},
    error=None,  # string if the tool failed
)
```

### `event.retrieval(**kwargs)`

Record a knowledge base query.

```python
event.retrieval(
    name="vector_store",
    query="quarterly revenue",
    results=[{"text": "...", "score": 0.95}],
)
```

### `event.memory_read(**kwargs)` / `event.memory_write(**kwargs)`

Record memory operations.

```python
event.memory_read(name="user_prefs", key="language", value="en")
event.memory_write(name="cache", key="result", value={"answer": "42"})
```

### `event.step(**kwargs)`

Record a generic step (for custom step types).

```python
event.step(
    type="custom_operation",
    name="validate",
    input={"data": "..."},
    output={"valid": True},
)
```

## Analysis

### `register_detector(name)`

Register a custom failure detector.

```python
from agent_replay.analysis import register_detector, Finding, taxonomy

@register_detector("my_check")
def my_check(run, steps):
    # return a list of Finding objects
    return []
```

### `Finding`

A detected issue in a run.

- `failure_type` — One of the taxonomy types (e.g., `taxonomy.HALLUCINATED_TOOL_ARGUMENT`)
- `detector_name` — Which detector found it
- `description` — Human-readable explanation
- `step_id` (optional) — The step where the issue was found
- `confidence` (optional) — 0.0 to 1.0
- `severity` (optional) — `HIGH`, `MEDIUM`, or `LOW`

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `AGENT_REPLAY_DB` | `~/.agent-replay/traces.db` | Database path |
| `AGENT_REPLAY_METADATA_ONLY` | `0` | Drop body payloads when `1` |
| `AGENT_REPLAY_CAPTURE_BODIES` | `1` | Same as above when `0` |
