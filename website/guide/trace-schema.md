# Trace Schema

Agent Replay records two types of structured data: **Runs** and **Steps**.

## Run

A Run represents one complete agent execution.

| Field | Type | Description |
|---|---|---|
| `run_id` | string | Unique identifier (`run_<12hex>`) |
| `agent_name` | string | Name of the agent |
| `task` | string | Description of the task |
| `started_at` | ISO datetime | When the run started |
| `ended_at` | ISO datetime | When the run ended |
| `status` | enum | `running`, `success`, or `failed` |
| `cost_usd` | float | Total cost in USD (optional) |
| `latency_ms` | int | Total duration in milliseconds |
| `metadata` | object | Arbitrary key-value pairs |
| `schema_version` | string | Trace format version |

## Step

A Step represents one state transition within a run.

| Field | Type | Description |
|---|---|---|
| `step_id` | string | Unique identifier (`<type>_<n>`) |
| `run_id` | string | Parent run |
| `type` | enum | `llm_call`, `tool_call`, `retrieval`, `memory_read`, `memory_write` |
| `name` | string | Operation name |
| `input` | any | What went in |
| `output` | any | What came out |
| `state_before` | any | State snapshot before the step |
| `state_after` | any | State snapshot after the step |
| `error` | string | Error message if the step failed |
| `usage` | object | Token usage, latency, cost |
| `parent_step_id` | string | For nested steps |
| `timestamp` | ISO datetime | When the step occurred |
| `metadata` | object | Arbitrary key-value pairs |

## Step types

### `llm_call`

A call to a language model. Records provider, model, input messages, output message, and token usage.

### `tool_call`

An invocation of an external tool or function. Records tool name, input arguments, output, and any error.

### `retrieval`

A query to a knowledge base or vector store. Records query, results, and relevance scores.

### `memory_read` / `memory_write`

Read from or write to the agent's memory system. Records key, value, and namespace.

## Forward compatibility

The schema is versioned (`SCHEMA_VERSION`). Unknown fields are preserved in `metadata` via `from_dict`, so traces from newer versions can still be read by older analysis tools.

## JSON format

Export and import traces as JSON:

```bash
agent-replay export latest --format json > trace.json
agent-replay import trace.json
```

The JSON format is the canonical interchange format. Any language can produce it — see the [TypeScript SDK](/api/typescript-sdk) for a non-Python example.
