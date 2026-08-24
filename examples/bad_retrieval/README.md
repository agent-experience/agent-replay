# Failure: bad retrieval

The retriever returns a shipping FAQ (low relevance scores) when asked about the refund
policy, and the agent answers from that irrelevant context.

```bash
python examples/bad_retrieval/main.py
agent-replay show latest
```

What to look for: the `retrieval` step's `output` shows low-score, off-topic chunks, and the
following `llm_call` produces an answer grounded in the wrong material — the `bad_retrieval`
failure mode.
