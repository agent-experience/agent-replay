# Security & Privacy

## Traces can contain sensitive data

Agent Replay records the inputs and outputs of your agent. **A trace may contain prompts,
tool results, retrieved documents, PII, API keys, and other secrets.** Treat trace files
(and any exports) with the same care as application logs that contain user data.

Agent Replay is **local-first**: traces are written to a local SQLite database
(`~/.agent-replay/traces.db` by default) and are **never uploaded** anywhere. There is no
hosted service and no telemetry back to the project.

## Reducing what you capture

- `AGENT_REPLAY_METADATA_ONLY=1` — record step structure but drop body payloads.
- `AGENT_REPLAY_CAPTURE_BODIES=0` — same effect as metadata-only.
- `trace(..., redact=fn)` — pass a hook that receives the sensitive fields
  (`input`, `output`, `state_before`, `state_after`) and returns a scrubbed copy.

**Always sanitize a trace before sharing it** in a bug report or exporting it to another
system. A standalone `sanitize` command and `.agent-replayignore` support are planned for a
later release.

## Reporting a vulnerability

If you discover a security issue, please **do not open a public issue**. Instead, email the
maintainers at **security@agent-experience.dev** with a description and reproduction steps.
We'll acknowledge within a few business days and keep you updated on a fix.
