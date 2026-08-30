# Failure Analysis

Agent Replay's analysis engine runs deterministic detectors over recorded traces to identify why agents fail. No LLM calls required — results come back in milliseconds.

## How it works

```bash
agent-replay analyze latest
```

The engine:

1. Loads the recorded run and its steps from the local database
2. Runs all registered detectors against the trace
3. Aggregates findings by severity and confidence
4. Suggests a replay point (the step to focus on)

## Deterministic detectors

Ten built-in detectors cover the most common failure patterns:

| Detector | Severity | What it catches |
|---|---|---|
| `hallucinated_tool_argument` | HIGH | Agent invents non-existent parameters |
| `ignored_tool_result` | HIGH | Agent ignores correct tool output |
| `unsafe_write_action` | HIGH | Destructive action without confirmation |
| `permission_mismatch` | HIGH | Unauthorized action attempts |
| `final_answer_conflict` | HIGH | Conclusion contradicts evidence |
| `bad_retrieval` | MEDIUM | Retrieved context is irrelevant |
| `stale_memory` | MEDIUM | Acting on outdated memory |
| `loop_detected` | MEDIUM | Repeating the same action |
| `context_pollution` | LOW | Context grows without value |
| `excessive_retry` | LOW | Retrying without changing approach |

See [10 Agent Failure Patterns](/failure-patterns) for detailed descriptions and examples.

## LLM-assisted detectors

For deeper analysis, plug in a model of your choice:

```python
from agent_replay.analysis.llm import LLMFailureClassifier, LLMRootCauseDetector

# Any callable that takes a prompt string and returns a string
def my_llm(prompt: str) -> str:
    return openai.chat(model="gpt-4", messages=[{"role": "user", "content": prompt}])

classifier = LLMFailureClassifier(llm=my_llm)
root_cause = LLMRootCauseDetector(llm=my_llm)
```

LLM detectors are optional and provider-agnostic.

## Custom detectors

Register your own detector in a few lines:

```python
from agent_replay.analysis import register_detector, Finding, taxonomy

@register_detector("token_budget")
def token_budget(run, steps):
    total = sum(s.usage.get("input_tokens", 0) + s.usage.get("output_tokens", 0)
                for s in steps if s.usage)
    if total > 100_000:
        return [Finding(
            taxonomy.EXCESSIVE_RETRY,
            "token_budget",
            f"Run used {total:,} tokens — check for unnecessary retries.",
        )]
    return []
```

Load custom detectors via CLI:

```bash
agent-replay analyze latest --plugin my_detectors
```

## Cross-run statistics

```bash
agent-replay stats
```

Aggregates failure patterns across all recorded runs: which detectors fire most often, which agents fail most, and trending severity over time.

## CI integration

Use JSON output for automated quality gates:

```bash
agent-replay analyze latest --format json | jq '.severity'
```

A non-zero exit code when high-severity findings are detected makes it easy to integrate into CI pipelines.
