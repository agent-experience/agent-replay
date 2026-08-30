---
title: 10 AI Agent Failure Patterns Every Developer Should Know
description: Hallucinated arguments, ignored tool results, infinite loops — ten deterministic failure patterns that cause AI agents to silently fail, with detection rules and fix examples.
head:
  - - meta
    - property: og:title
      content: 10 AI Agent Failure Patterns Every Developer Should Know
  - - meta
    - property: og:description
      content: Hallucinated arguments, ignored tool results, infinite loops — ten deterministic failure patterns that cause AI agents to silently fail, with detection rules and fix examples.
  - - meta
    - property: og:type
      content: article
---

# 10 AI Agent Failure Patterns and How to Detect Them

Traditional software crashes loudly. AI agents fail silently — reporting success while hallucinating arguments, ignoring tool results, or contradicting their own evidence. Agent Replay ships ten deterministic detectors that identify these failures from recorded [traces](/guide/trace-schema) without making any LLM calls. Results return in milliseconds.

| # | Pattern | Severity | One-line description |
|---|---|---|---|
| 1 | [Hallucinated Tool Arguments](#_1-hallucinated-tool-arguments) | High | Agent invents parameters, IDs, or types that don't exist |
| 2 | [Ignored Tool Result](#_2-ignored-tool-result) | High | Agent retrieves correct data, then doesn't use it |
| 3 | [Unsafe Write Action](#_3-unsafe-write-action) | High | Destructive operation runs without confirmation |
| 4 | [Permission Mismatch](#_4-permission-mismatch) | High | Agent retries or continues after authorization denial |
| 5 | [Final Answer Conflict](#_5-final-answer-conflict) | High | Conclusion contradicts evidence gathered during execution |
| 6 | [Bad Retrieval](#_6-bad-retrieval) | Medium | Retrieved context is irrelevant to the query |
| 7 | [Stale Memory](#_7-stale-memory) | Medium | Agent acts on information invalidated by a later step |
| 8 | [Loop Detected](#_8-loop-detected) | Medium | Same action repeats without progress |
| 9 | [Context Pollution](#_9-context-pollution) | Low | Irrelevant context accumulates, degrading later decisions |
| 10 | [Excessive Retry](#_10-excessive-retry) | Low | Failing operation retried without changing approach |

## High Severity

### 1. Hallucinated Tool Arguments

**What happens:** The agent invents a tool parameter that doesn't exist, passes a wrong type, or fabricates an ID. This is the agent equivalent of a compiler error — except no compiler stops it.

**Example:**

```python
# Agent calls:
database.query(table="users_v3")
# Actual table name: "users"
# Tool returns: TableNotFoundError
# Agent continues as if it succeeded
```

**Detection rule:** Flag tool calls that returned errors indicating invalid arguments, missing parameters, or unknown entities. Cross-reference argument values against known schemas when available.

### 2. Ignored Tool Result

**What happens:** A tool returns a correct and relevant result, but the agent's next LLM call doesn't reference or use it. The information was retrieved successfully — then silently dropped.

**Example:**

```python
# Step 3: search_pricing(product="enterprise")
# → Returns: {"monthly": "$499", "annual": "$4,990"}
#
# Step 4: LLM generates summary
# → "Please contact sales for pricing information."
# The pricing data was right there.
```

**Detection rule:** Compare tool outputs with subsequent LLM inputs. When a tool returns structured data and the next LLM response contains none of its key values, flag the gap.

### 3. Unsafe Write Action

**What happens:** The agent performs a destructive operation — delete, overwrite, send — without the expected confirmation step or guard. Users often discover the damage after the run ends.

**Detection rule:** Flag tool calls with write/delete/send semantics that lack preceding confirmation patterns in the trace.

### 4. Permission Mismatch

**What happens:** The agent attempts an action it isn't authorized to perform, gets denied, and either retries the same call uselessly or proceeds with incorrect assumptions about what happened.

**Detection rule:** Identify tool calls that return 401/403/permission errors followed by identical retries or continued execution that assumes the action succeeded.

### 5. Final Answer Conflict

**What happens:** The agent's final response contradicts evidence it gathered during execution. The conclusion doesn't match the data — and without trace analysis, nobody notices.

**Example:**

```python
# Step 5: check_service_status("payments")
# → Returns: {"status": "down", "since": "14:30 UTC"}
#
# Step 8: Final answer
# → "All systems operational. No issues detected."
# The payments service is still down.
```

**Detection rule:** Extract factual claims from the final LLM output and compare against tool results and observations recorded earlier in the trace.

## Medium Severity

### 6. Bad Retrieval

**What happens:** The agent queries a knowledge base or vector store, but the returned documents are irrelevant. The agent then reasons over wrong context — garbage in, confident answer out.

**Example:** Agent asks about "pricing tiers" but retrieval returns documentation about "API authentication." The agent proceeds to discuss pricing using authentication docs as evidence.

**Detection rule:** Measure semantic overlap between the retrieval query and returned results. Flag retrievals where similarity scores are below threshold or where result content shares no key terms with the query.

### 7. Stale Memory

**What happens:** The agent reads from memory and acts on information that was already updated or invalidated by a later step in the same run.

**Example:** At step 2, the agent reads `user.plan = "free"` from memory. At step 5, a tool call upgrades the user to "pro." At step 7, the agent tells the user they can't access premium features — still using the stale value from step 2.

**Detection rule:** Track all memory reads and writes within a run. Flag cases where a read value is contradicted by a subsequent write to the same key before the read value is used.

### 8. Loop Detected

**What happens:** The agent repeats the same action multiple times without making progress — same tool call, same arguments, same result. Tokens burn while nothing changes.

**Example:**

```python
# Step 3: web_search("company quarterly results") → timeout
# Step 4: web_search("company quarterly results") → timeout
# Step 5: web_search("company quarterly results") → timeout
# Step 6: web_search("company quarterly results") → timeout
# Agent never changes query or tries a different tool
```

**Detection rule:** Identify sequences of three or more tool calls with identical or near-identical names and arguments within a single run.

## Low Severity

### 9. Context Pollution

**What happens:** The agent's context window accumulates irrelevant information from previous steps. By step 10, the model is reasoning over a noisy mix of outdated search results, failed tool outputs, and stale observations — degrading the quality of every subsequent decision.

**Detection rule:** Measure context growth rate across steps. Flag runs where context size increases significantly without corresponding new information gain (e.g., repeated error messages or duplicate retrieval results being appended).

### 10. Excessive Retry

**What happens:** The agent retries a failing operation more than necessary, wasting tokens and time without changing its approach. Unlike [Loop Detected](#_8-loop-detected), the agent may vary its arguments slightly, but the underlying strategy doesn't change.

**Detection rule:** Count sequential retries of the same operation type. Flag runs that exceed configurable thresholds (default: 3 retries without a strategy change).

## Running the Detectors

All ten detectors run automatically over any recorded [trace](/guide/trace-schema):

```bash
# Analyze the most recent run
agent-replay analyze latest

# Analyze a specific run
agent-replay analyze run_a1b2c3d4e5f6

# Machine-readable output for CI pipelines
agent-replay analyze latest --format json

# Aggregate failure statistics across all runs
agent-replay stats
```

Example output:

```text
Likely root cause:
  • Tool 'ticketing.update' returned an error but the agent continued
    and treated the run as successful. — ignored_tool_result
Severity: high   Confidence: 0.70
Suggested replay point: step tool_call_3
```

### Writing a Custom Detector

Extend the built-in set with your own domain-specific checks:

```python
from agent_replay.analysis import register_detector, Finding, taxonomy

@register_detector("cost_guard")
def cost_guard(run, steps):
    if run.cost_usd and run.cost_usd > 1.0:
        return [Finding(
            taxonomy.EXCESSIVE_RETRY,
            "cost_guard",
            f"Run cost ${run.cost_usd:.2f} — review for wasted retries.",
        )]
    return []
```

Custom detectors are loaded with the `--plugin` flag:

```bash
agent-replay analyze latest --plugin my_detectors
```

## Next Steps

- [Get started](/guide/getting-started) — record your first trace in under 5 minutes
- [Failure analysis guide](/guide/failure-analysis) — how root cause analysis works
- [Trace schema](/guide/trace-schema) — understand the data behind each detection
- [CLI reference](/api/cli) — full command documentation
