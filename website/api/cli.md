# CLI Reference

## Commands

### `agent-replay list`

List all recorded runs.

```bash
agent-replay list
```

Displays a table with run ID, agent name, task, status, duration, and timestamp.

### `agent-replay show <run>`

Display the timeline of a run as a tree.

```bash
agent-replay show latest
agent-replay show run_49fea4df07cc
```

### `agent-replay replay <run>`

Playback a run without calling any external models or tools. Steps are re-emitted in order with their recorded inputs and outputs.

```bash
agent-replay replay latest
```

### `agent-replay analyze <run>`

Run failure detectors and produce an explainable report.

```bash
agent-replay analyze latest
agent-replay analyze latest --format json     # machine-readable
agent-replay analyze latest --plugin my_module # custom detectors
```

**Output includes:**
- Likely root cause with confidence scores
- Severity rating (high / medium / low)
- Suggested replay point
- Individual findings from each detector

### `agent-replay stats`

Aggregate failure statistics across all recorded runs.

```bash
agent-replay stats
```

Shows which failure patterns occur most often, which agents fail most, and severity distribution.

### `agent-replay export <run>`

Export a run in JSON or OTLP format.

```bash
agent-replay export latest --format json
agent-replay export latest --format otlp
```

### `agent-replay import <file>`

Import a JSON trace (single or array). Accepts files or stdin.

```bash
agent-replay import trace.json
agent-replay import -                  # read from stdin
agent-replay import trace.json --overwrite  # replace existing run
```

### `agent-replay sanitize <run>`

Export a run with secrets scrubbed, safe for sharing.

```bash
agent-replay sanitize latest > clean-trace.json
```

## Global options

| Option | Description |
|---|---|
| `latest` | Shorthand for the most recently recorded run |
| `--format` | Output format (`json`, `otlp`, `text`) |
| `--plugin` | Load custom detector module |

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `AGENT_REPLAY_DB` | `~/.agent-replay/traces.db` | SQLite database path |
| `AGENT_REPLAY_METADATA_ONLY` | `0` | Record structure only, drop payloads |
| `AGENT_REPLAY_CAPTURE_BODIES` | `1` | Same as above when set to `0` |
