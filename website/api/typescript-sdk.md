# TypeScript SDK

The official TypeScript recorder [`@agent-replay/record`](https://github.com/agent-experience/agent-replay/tree/main/sdks/typescript) produces canonical JSON traces that the Python CLI can import and analyze.

## Install

```bash
npm install @agent-replay/record
```

Requires Node.js 22.6+. Zero runtime dependencies.

## Quick start

```ts
import { trace } from "@agent-replay/record";

await trace(
  { agent: "research-agent", task: "Find pricing", out: "trace.json" },
  async (run) => {
    run.llmCall({
      provider: "anthropic",
      model: "claude-4",
      inputMessages: [{ role: "user", content: "Find pricing" }],
      outputMessage: { role: "assistant", content: "Searching..." },
      usage: { inputTokens: 100, outputTokens: 50 },
    });

    run.toolCall({
      name: "web_search",
      input: { query: "pricing page" },
      output: { url: "https://example.com/pricing" },
    });
  }
);
```

Then analyze with the Python CLI:

```bash
agent-replay import trace.json
agent-replay analyze latest
```

## API

### `trace(options, fn)`

Records a run and writes it to a JSON file.

**Options:**
- `agent` (string) — Agent name
- `task` (string) — Task description
- `out` (string) — Output file path
- `metadata` (object, optional) — Arbitrary metadata

### `run.llmCall(options)`

Record a language model call.

### `run.toolCall(options)`

Record a tool invocation.

### `run.retrieval(options)`

Record a retrieval query.

### `run.memoryRead(options)` / `run.memoryWrite(options)`

Record memory operations.

### `scrub(data, patterns?)`

Redact sensitive fields before recording. Uses `DEFAULT_SECRET_PATTERNS` (11 patterns) by default.

```ts
import { scrub } from "@agent-replay/record";

const clean = scrub({ api_key: "sk-123", data: "safe" });
// { api_key: "[REDACTED]", data: "safe" }
```
