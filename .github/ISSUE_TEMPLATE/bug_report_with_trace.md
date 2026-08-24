---
name: Bug report with trace
about: Report an agent failure, ideally with a sanitized trace
title: "[bug] "
labels: bug
---

## What happened

<!-- A clear description of the bug or the agent failure you observed. -->

## Sanitized trace

> ⚠️ **Before pasting:** a trace can contain prompts, tool results, PII, and secrets.
> Please sanitize it first (see SECURITY.md). You can capture with
> `AGENT_REPLAY_METADATA_ONLY=1` or scrub via a `redact=` hook, then export with:
>
> ```bash
> agent-replay export <run_id> --format json --output run.json
> ```

<details>
<summary>trace (JSON)</summary>

```json
PASTE SANITIZED TRACE HERE
```

</details>

## Expected behavior

<!-- What you expected the agent (or Agent Replay) to do. -->

## Environment

- Agent Replay version: <!-- python -c "import agent_replay; print(agent_replay.__version__)" -->
- Python version:
- OS:

## Additional context

<!-- Anything else that helps us reproduce. -->
