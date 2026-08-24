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

See [`SECURITY.md`](SECURITY.md) before sharing a trace.

## Roadmap

Agent Replay ships in phases (see [`docs/whitepaper.md`](docs/whitepaper.md)):

1. **Trace + Replay** — record traces, inspect, playback. *(this release, Phase 1)*
2. **Failure Analysis + Eval** — detectors and explainable failure reports.
3. **Checkpoint + Fork** — fork a run from any step and diff branches.
4. **Experience Memory** — turn past runs into reusable, retrievable lessons.

## Non-goals (Phase 1)

Agent Replay is deliberately narrow to start. Phase 1 does **not** re-execute side-effectful
tools, do automatic root-cause analysis, provide checkpoint/fork, ship a hosted dashboard,
or attempt OS-level deterministic replay. It implements **semantic replay** for agents, not
byte-level record/replay.

## Research grounding

Agent Replay builds on ReAct (reasoning + acting traces), agent evaluation work
(AgentBench, WebArena), reflection and experience learning (Reflexion, ExpeL, Voyager),
long-term memory (Generative Agents, MemGPT), OpenTelemetry's GenAI semantic conventions,
and the systems record/replay tradition (rr, CRIU, Firecracker). See
[`docs/research.md`](docs/research.md).

## License

Apache-2.0 — see [`LICENSE`](LICENSE).
