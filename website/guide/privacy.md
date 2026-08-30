# Privacy & Redaction

Agent Replay is local-first: traces are written to disk and never uploaded to any service. But traces can contain prompts, tool results, PII, and secrets. Agent Replay provides multiple layers of control.

## Metadata-only mode

Record step structure but drop all body payloads:

```bash
export AGENT_REPLAY_METADATA_ONLY=1
# or
export AGENT_REPLAY_CAPTURE_BODIES=0
```

This records which steps happened, their types, timing, and errors — but not the actual content of LLM messages, tool inputs/outputs, or retrieval results.

## Redaction hooks

Pass a function to scrub sensitive fields before they are stored:

```python
from agent_replay import trace

def redact(data):
    if isinstance(data, dict):
        return {k: "***" if "password" in k.lower() else redact(v)
                for k, v in data.items()}
    return data

with trace("my-agent", task="Process data", redact=redact):
    # All event data passes through your redact function
    ...
```

## .agent-replayignore

Create a `.agent-replayignore` file in your project root with glob patterns for fields to redact:

```text
*password*
*secret*
*token*
authorization
*api_key*
*credit_card*
```

Matching fields are redacted at any depth when recorded.

## Sanitize for sharing

Export a run with secrets scrubbed, safe to attach to a bug report:

```bash
agent-replay sanitize latest > clean-trace.json
```

The sanitize command applies 11 built-in secret patterns (passwords, API keys, tokens, SSNs, etc.) and replaces matches with `[REDACTED]`.

## What is never stored

- Agent Replay does not transmit data to any external service
- No telemetry, analytics, or usage tracking
- No account or API key required
- The SQLite database stays at `~/.agent-replay/traces.db` (configurable via `AGENT_REPLAY_DB`)
