# 10 Common AI Agent Failure Patterns

Agent Replay includes ten built-in deterministic detectors that identify the most common ways AI agents fail. These detectors run over recorded traces without making any LLM calls — results come back in milliseconds.

## High Severity

### 1. Hallucinated Tool Arguments

**What happens:** The agent invents a tool parameter that doesn't exist, passes a wrong type, or fabricates an ID.

**Example:** Agent calls `database.query(table="users_v3")` but the table is actually named `users`. The tool returns an error, but the agent may continue as if it succeeded.

**Detector:** Checks for tool calls that returned errors indicating invalid arguments, missing parameters, or unknown entities.

### 2. Ignored Tool Result

**What happens:** A tool returns a correct and relevant result, but the agent's next LLM call doesn't reference or use it.

**Example:** A search tool returns pricing data, but the agent's summary doesn't mention any prices. The information was retrieved but dropped.

**Detector:** Compares tool outputs with subsequent LLM inputs to identify results that were never incorporated.

### 3. Unsafe Write Action

**What happens:** The agent performs a destructive operation (delete, overwrite, send) without the expected confirmation step or guard.

**Detector:** Flags tool calls with write/delete/send semantics that lack preceding confirmation patterns.

### 4. Permission Mismatch

**What happens:** The agent attempts an action it isn't authorized to perform, gets denied, and either retries uselessly or proceeds with incorrect assumptions.

**Detector:** Identifies tool calls that return permission/authorization errors followed by retries or continued execution.

### 5. Final Answer Conflict

**What happens:** The agent's final response contradicts evidence gathered during execution. The conclusion doesn't match the data.

**Example:** Tool calls reveal a service is down, but the agent reports "all systems operational."

**Detector:** Compares claims in the final LLM output against tool results and earlier observations.

## Medium Severity

### 6. Bad Retrieval

**What happens:** Retrieved context is irrelevant to the query. The agent asks about pricing but gets documentation about authentication.

**Detector:** Measures semantic overlap between retrieval queries and returned results.

### 7. Stale Memory

**What happens:** The agent reads from memory and acts on information that was updated or invalidated by a later step.

**Detector:** Tracks memory reads and writes to identify cases where a read precedes a contradicting write within the same run.

### 8. Loop Detected

**What happens:** The agent repeats the same action multiple times without making progress. Same tool call, same arguments, same result.

**Detector:** Identifies sequences of identical or near-identical tool calls within a run.

## Low Severity

### 9. Context Pollution

**What happens:** The agent's context accumulates irrelevant information from previous steps, degrading the quality of later decisions.

**Detector:** Measures context growth rate and identifies steps where context size increases without corresponding information gain.

### 10. Excessive Retry

**What happens:** The agent retries a failing operation more than necessary, wasting tokens and time without changing its approach.

**Detector:** Counts sequential retries of the same operation and flags runs that exceed configurable thresholds.

---

## Using the detectors

```bash
# Analyze the most recent run
agent-replay analyze latest

# Machine-readable output for CI
agent-replay analyze latest --format json

# Aggregate statistics across all runs
agent-replay stats

# Add your own custom detector
agent-replay analyze latest --plugin my_detectors
```

### Write a custom detector

```python
from agent_replay.analysis import register_detector, Finding, taxonomy

@register_detector("cost_guard")
def cost_guard(run, steps):
    if run.cost_usd and run.cost_usd > 1.0:
        return [Finding(
            taxonomy.EXCESSIVE_RETRY,
            "cost_guard",
            f"Run cost ${run.cost_usd:.2f} — unusually expensive.",
        )]
    return []
```
