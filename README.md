# Agent Replay

> **Time-travel debugging for AI agents.**

Agent Replay is a **local-first, open-source debugging layer for AI agents**. It records
structured traces of every agent run — LLM calls, tool calls, retrievals, memory access —
so you can inspect *why* a run went wrong, replay the trajectory, and (in later phases) fork
from any step and turn past runs into reusable experience.

Traditional observability tells you **what happened**. Agent Replay is built to answer the
harder question: **what would have happened if you changed the decision at step N?**

Traces stay on your machine. No account, no hosted service, no data leaves your laptop.

```text
record → inspect → replay → fork → learn
```

## Install

```bash
pip install agent-replay
```

## Quickstart (under 5 minutes)

Instrument your agent by wrapping the run in a `trace()` block and recording events:

```python
from agent_replay import trace, event

with trace("research-agent", task="Find latest pricing"):
    event.llm_call(
        provider="openai",
        model="gpt-5.5",
        input_messages=[{"role": "user", "content": "Find latest pricing"}],
        output_message={"role": "assistant", "content": "I'll search the pricing page."},
        usage={"input_tokens": 1200, "output_tokens": 300},
    )
    event.tool_call(
        name="browser.search",
        input={"query": "pricing page"},
        output={"url": "https://example.com/pricing"},
    )
```

Then inspect from the terminal:

```bash
agent-replay list                       # every recorded run
agent-replay show latest                # the timeline of the most recent run
agent-replay replay latest              # playback (no models/tools are called)
agent-replay export latest --format json
agent-replay export latest --format otlp
```

Traces are stored in a local SQLite database at `~/.agent-replay/traces.db` (override with
the `AGENT_REPLAY_DB` environment variable).

## Try the examples

No API keys required — each example uses a mock LLM and mock tools:

```bash
python examples/minimal_openai_agent/main.py   # happy path
python examples/failed_tool_call/main.py        # hallucinated tool argument
python examples/bad_retrieval/main.py           # off-task retrieval
python examples/ignored_tool_result/main.py     # tool error ignored by the agent
agent-replay show latest
```

## Find why your agent failed

Once a run is recorded, ask Agent Replay what went wrong:

```bash
agent-replay analyze latest
```

```text
support-agent  run_49fea4df07cc  success
Close ticket T-9

Likely root cause:
  • Tool 'ticketing.update' returned an error but the agent continued and treated
    the run as successful. (tool_call_1) — ignored_tool_result, confidence 0.70
  • Final answer claims success, but an earlier tool observation was an error
    (from tool_call_1). (llm_call_2) — final_answer_conflict, confidence 0.70

Suggested replay point: before tool_call_1
Severity: high   Confidence: 0.70
```

The run *reported* success — it never raised — yet Agent Replay flags why it actually failed.

Analysis runs ten built-in **deterministic detectors** over the recorded trace — no model
calls required — covering the failure taxonomy (hallucinated tool arguments, ignored tool
results, bad retrieval, stale memory, context pollution, excessive retries, loops, unsafe
writes, permission mismatches, final-answer conflicts). Two optional **LLM-assisted
detectors** (`LLMFailureClassifier`, `LLMRootCauseDetector`) plug in a model of your choice.

```bash
agent-replay analyze latest --format json     # machine-readable eval report
agent-replay stats                            # failure statistics across all runs
agent-replay analyze latest --plugin my_detectors   # add your own detectors
```

Write a custom detector in a few lines:

```python
from agent_replay.analysis import register_detector, Finding, taxonomy

@register_detector("my_check")
def my_check(run, steps):
    if run.cost_usd and run.cost_usd > 1.0:
        return [Finding(taxonomy.EXCESSIVE_RETRY, "my_check", "Run was unusually expensive.")]
    return []
```

## What Agent Replay records

| Event | Recorder |
|---|---|
| Model call | `event.llm_call(provider, model, input_messages, output_message, usage=...)` |
| Tool call | `event.tool_call(name, input, output, error=...)` |
| Retrieval | `event.retrieval(name, query, results)` |
| Memory read/write | `event.memory_read(...)` / `event.memory_write(...)` |

Every run has a `run_id`, every step a `step_id`, and the trace schema is versioned
(`SCHEMA_VERSION`) and forward-compatible.

## Privacy

Agent Replay is **local-first**: traces are written to disk and **never uploaded**. But a
trace can contain prompts, tool results, PII, and secrets. Controls:

- `AGENT_REPLAY_METADATA_ONLY=1` — record step structure but drop body payloads.
- `AGENT_REPLAY_CAPTURE_BODIES=0` — same effect.
- `trace(..., redact=fn)` — pass a hook to scrub sensitive fields before they are stored.
- `.agent-replayignore` — list key glob patterns (e.g. `*password*`, `authorization`); matching
  fields are redacted at any depth when recorded.
- `agent-replay sanitize latest` — export a run with secret-bearing fields scrubbed, safe to
  attach to a bug report.

See [`SECURITY.md`](SECURITY.md) before sharing a trace.

## Roadmap

Agent Replay ships in phases (see [`docs/whitepaper.md`](docs/whitepaper.md)):

1. **Trace + Replay** — record traces, inspect, playback. *(shipped)*
2. **Failure Analysis + Eval** — detectors and explainable failure reports. *(this release, Phase 2)*
3. **Checkpoint + Fork** — fork a run from any step and diff branches.
4. **Experience Memory** — turn past runs into reusable, retrievable lessons.

## Non-goals (Phases 1–2)

Agent Replay is deliberately narrow to start. It does **not** re-execute side-effectful
tools, provide checkpoint/fork, ship a hosted dashboard, or attempt OS-level deterministic
replay. It implements **semantic replay** for agents, not byte-level record/replay, and its
failure detectors surface *signals to confirm*, not proofs.

## Research grounding

Agent Replay builds on ReAct (reasoning + acting traces), agent evaluation work
(AgentBench, WebArena), reflection and experience learning (Reflexion, ExpeL, Voyager),
long-term memory (Generative Agents, MemGPT), OpenTelemetry's GenAI semantic conventions,
and the systems record/replay tradition (rr, CRIU, Firecracker). See
[`docs/research.md`](docs/research.md).

## License

Apache-2.0 — see [`LICENSE`](LICENSE).
