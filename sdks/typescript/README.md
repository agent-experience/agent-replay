# @agent-replay/record

**Debug your TypeScript / JavaScript agent with [Agent Replay](../../).**

This is a tiny recorder: you add a few lines to your agent, it writes a `trace.json`, and the
Agent Replay CLI reads that file to show the timeline, find failures, and replay the run.

```
your TS agent  ──record──▶  trace.json  ──import──▶  agent-replay analyze
   (this SDK)                              (the Python tool does the analysis)
```

The recorder has **zero dependencies** and does *no analysis* — all the smarts (failure
detectors, `show`, `replay`, `stats`) live once in the Python engine and work on a trace from
any language. Requires **Node ≥ 22.6** and, for the analysis step, the
[`agent-replay`](../../) Python CLI (`pip install agent-replay`).

---

## 1. Record (in your agent)

```ts
import { trace } from "@agent-replay/record";

const { runId } = await trace(
  { agent: "research-agent", task: question, out: "trace.json" },
  async (run) => {
    const reply = await client.messages.create({ model, messages, tools });

    run.llmCall({
      provider: "anthropic",
      model,
      inputMessages: messages,
      outputMessage: { role: "assistant", content: reply.text }, // ← use { role, content }
    });

    const { output, error } = await runTool(name, input);
    run.toolCall({ name, input, output, error }); // ← pass tool errors through

    return reply.text;
  },
);
// trace.json now written. The run is marked "failed" automatically if the callback throws.
```

That's the whole integration. Two rules make the failure detectors work:
- record the model's answer as `{ role: "assistant", content: "..." }` (so text detectors can read it);
- pass tool failures through `error` (so a swallowed tool error is visible).

## 2. Import + analyze (in your terminal)

```bash
agent-replay import trace.json     # load it into the local store
agent-replay show latest           # the timeline
agent-replay analyze latest        # find likely failures
agent-replay stats                 # stats across runs
```

## Try the runnable example

A complete mock ReAct agent (no API key, no network) lives in
[`examples/react-agent`](examples/react-agent). It ships three scenarios:

```bash
cd examples/react-agent

# happy path → correct answer, no findings
node --experimental-strip-types run.ts --scenario happy
#   A: Here's what I found: the calculation gives 36; Paris.

# a debuggable failure → the agent ignores a tool error and claims success
node --experimental-strip-types run.ts --scenario buggy

# secrets in a tool input → redacted before they touch disk
node --experimental-strip-types run.ts --scenario redaction
```

Then analyze the buggy run:

```bash
agent-replay import trace.json
agent-replay analyze latest
```
```text
research-agent  run_8a23a59d735e  success  5ms
What's the current weather in Zzyzx?

Likely root cause:
  • Tool 'get_weather' returned an error but the agent continued and treated the
run as successful. (tool_call_2) — ignored_tool_result, confidence 0.70
  • Final answer claims success, but an earlier tool observation was an error
(from tool_call_2). (llm_call_3) — final_answer_conflict, confidence 0.70

Suggested replay point: before tool_call_2
Severity: high   Confidence: 0.70
```

The run's own status is `success` — the agent *thought* it was done. Agent Replay catches the
silent failure. This is the exact same report the Python agent produces; the analysis doesn't
care which language recorded the trace.

## Redaction

Secrets never need to reach disk. Pass a `redact` hook; the SDK ships `scrub` +
`DEFAULT_SECRET_PATTERNS` (the same key globs as the Python SDK), and you can add your own:

```ts
import { scrub, DEFAULT_SECRET_PATTERNS, trace } from "@agent-replay/record";

const patterns = [...DEFAULT_SECRET_PATTERNS, "*email*"]; // extend with app-specific PII keys
const redact = (fields) =>
  Object.fromEntries(Object.entries(fields).map(([k, v]) => [k, scrub(v, patterns)]));

await trace({ agent: "research-agent", task, redact, out: "trace.json" }, async (run) => { /* … */ });
```

In the redaction scenario, `api_key`, `token`, and `customer_email` are all stored as
`«redacted»`.

## API

| | |
|---|---|
| `trace({ agent, task?, redact?, metadata?, out? }, fn)` | Open a run, run `fn(run)`, mark it `success`/`failed`, write JSON to `out`. Returns `{ runId, result, trace }`. |
| `new Trace({ agent, task?, redact?, metadata? })` | Manual control: `.llmCall(...)`, `.toolCall(...)`, `.retrieval(...)`, `.end(status)`, `.write(path)`, `.toJSON()`. |
| `run.llmCall({ provider, model, inputMessages?, outputMessage?, usage?, error? })` | Record one model turn. |
| `run.toolCall({ name, input?, output?, error?, stateBefore?, stateAfter? })` | Record one tool call. |
| `scrub(value, patterns?)` / `DEFAULT_SECRET_PATTERNS` | Recursively redact values under secret-shaped keys. |

The output is the canonical Agent Replay trace format (`SCHEMA_VERSION` `0.1`) — exactly what
`agent-replay import` and `agent-replay export --format json` use, so it round-trips with the
Python SDK.

## Build (for publishing)

```bash
npm install
npm run build      # → dist/ (index.js + index.d.ts)
npm run typecheck
```

## License

Apache-2.0 — see [`../../LICENSE`](../../LICENSE).
