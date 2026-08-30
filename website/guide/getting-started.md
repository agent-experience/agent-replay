# Getting Started

## Install

```bash
pip install agent-replay
```

Requires Python 3.10+. Only two runtime dependencies: `typer` and `rich`.

## Record your first trace

Wrap your agent code in a `trace()` block and record events as they happen:

```python
from agent_replay import trace, event

with trace("my-agent", task="Summarize document"):
    # Record an LLM call
    event.llm_call(
        provider="openai",
        model="gpt-5.5",
        input_messages=[{"role": "user", "content": "Summarize this document"}],
        output_message={"role": "assistant", "content": "Here is the summary..."},
        usage={"input_tokens": 500, "output_tokens": 200},
    )

    # Record a tool call
    event.tool_call(
        name="read_file",
        input={"path": "report.pdf"},
        output={"content": "Q3 revenue increased 15%..."},
    )

    # Record a retrieval
    event.retrieval(
        name="vector_search",
        query="quarterly revenue",
        results=[{"text": "Revenue data...", "score": 0.92}],
    )
```

Traces are stored in `~/.agent-replay/traces.db` (SQLite). Override with `AGENT_REPLAY_DB`.

## Inspect from the terminal

```bash
agent-replay list              # all recorded runs
agent-replay show latest       # timeline of the most recent run
agent-replay replay latest     # playback without calling any external service
agent-replay analyze latest    # find what went wrong
agent-replay stats             # failure statistics across all runs
```

## Try the examples

No API keys required — each example uses mock LLMs and tools:

```bash
git clone https://github.com/agent-experience/agent-replay.git
cd agent-replay
pip install -e .

python examples/minimal_openai_agent/main.py   # happy path
python examples/failed_tool_call/main.py        # hallucinated tool argument
python examples/bad_retrieval/main.py           # off-task retrieval
python examples/ignored_tool_result/main.py     # tool error ignored by the agent
python examples/failure_gallery/main.py         # all 10 failure patterns

agent-replay show latest
agent-replay analyze latest
```

## Record from TypeScript

Use the official TypeScript SDK [`@agent-replay/record`](https://github.com/agent-experience/agent-replay/tree/main/sdks/typescript):

```ts
import { trace } from "@agent-replay/record";

await trace({ agent: "research-agent", task: "Find pricing", out: "trace.json" }, async (run) => {
  run.llmCall({ provider: "anthropic", model: "claude-4", inputMessages, outputMessage });
  run.toolCall({ name: "search", input, output });
});
```

Then import and analyze:

```bash
agent-replay import trace.json
agent-replay analyze latest
```

## Next steps

- Learn about the [10 built-in failure patterns](/failure-patterns)
- Understand the [trace schema](/guide/trace-schema)
- Set up [privacy controls](/guide/privacy)
