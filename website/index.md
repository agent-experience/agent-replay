---
layout: home
hero:
  name: Agent Replay
  text: Time-travel debugging for AI agents
  tagline: Record, replay, and analyze agent execution traces. Local-first, open-source, with built-in failure detection.
  actions:
    - theme: brand
      text: Get Started
      link: /guide/getting-started
    - theme: alt
      text: View on GitHub
      link: https://github.com/agent-experience/agent-replay
features:
  - icon: 🔍
    title: Record Every Step
    details: Capture LLM calls, tool invocations, retrievals, and memory operations with a single line of code. Traces are stored locally in SQLite — nothing leaves your machine.
  - icon: ⏪
    title: Replay Without Cost
    details: Re-run any agent execution without calling models or tools. Understand exactly what happened at each decision point, for free.
  - icon: 🐛
    title: 10 Built-in Failure Detectors
    details: Automatically identify hallucinated arguments, ignored tool results, bad retrieval, loops, context pollution, and 5 more failure patterns — no LLM required.
  - icon: 🌐
    title: Any Language
    details: Python SDK, TypeScript SDK, and a language-neutral JSON trace format. Record in any language, analyze everywhere.
  - icon: 🔒
    title: Privacy First
    details: Traces never leave your machine. Metadata-only mode, .agent-replayignore, custom redaction hooks, and a sanitize command for safe sharing.
  - icon: 📊
    title: Actionable Reports
    details: Get root cause analysis, severity ratings, suggested replay points, and cross-run failure statistics. Machine-readable JSON output for CI integration.
---

## Quick Example

```python
from agent_replay import trace, event

with trace("research-agent", task="Find latest pricing"):
    event.llm_call(
        provider="openai", model="gpt-5.5",
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

```bash
agent-replay analyze latest
```

```text
Likely root cause:
  • Tool 'ticketing.update' returned an error but the agent continued
    and treated the run as successful. — ignored_tool_result
Severity: high   Confidence: 0.70
```

The run *reported* success — it never raised — yet Agent Replay flags why it actually failed.
