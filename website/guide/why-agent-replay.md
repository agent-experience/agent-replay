# Why Agent Replay?

## The problem with debugging AI agents

Traditional software fails loudly: an exception, a stack trace, a crash. AI agents fail silently. An agent can report success while having ignored critical tool results, hallucinated function arguments, or contradicted its own evidence.

The debugging experience for AI agents today is broken:

**You can't reproduce the bug.** LLMs are non-deterministic. The same input at temperature 0, run 1,000 times, can produce 80 distinct outputs. The bug you saw won't happen again.

**Logs are useless.** Hundreds of lines of token input/output tell you what happened, but not why the agent made a wrong decision at step 7 out of 12.

**Re-running is expensive.** When an agent fails at step 9 of 10, starting over wastes all prior computation. Teams report spending $100+/day re-running failing agents.

**No root cause analysis.** Existing observability tools tell you a failure happened. None tell you why.

## How Agent Replay is different

### Record, don't re-run

Add one line to your agent code. Agent Replay captures every LLM call, tool invocation, retrieval, and memory operation. When something goes wrong, you already have the complete trace.

### Analyze, don't guess

Ten built-in deterministic detectors identify the most common agent failure patterns — hallucinated arguments, ignored results, bad retrieval, loops, and more. No LLM calls required for detection. Results in milliseconds.

### Replay for free

Re-run any recorded execution without calling models or tools. Inspect the same failing run as many times as you need, at zero cost.

### Local-first

Traces are stored in a local SQLite database. Nothing is uploaded anywhere. No account required. No hosted service. Your prompts, tool results, and agent behavior stay on your machine.

## Agent Replay vs. observability platforms

| | Agent Replay | LangSmith / Langfuse / Arize |
|---|---|---|
| **Data location** | Your machine (SQLite) | Their cloud |
| **Failure analysis** | 10 deterministic detectors + root cause | Trace viewing, manual inspection |
| **Replay** | Deterministic replay, no API calls | Re-run with live models |
| **Dependencies** | 2 (typer + rich) | Heavy SDK + cloud account |
| **Cost** | Free, forever | Free tier, then paid |
| **Privacy** | Built-in redaction, metadata-only mode | Varies |

Agent Replay is not a replacement for production observability. It's a debugging tool that answers the question your observability platform can't: **why did my agent make that decision?**
