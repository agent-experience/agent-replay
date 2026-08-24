"""Failure example: bad retrieval.

The retriever returns chunks that are poorly aligned with the task (a shipping FAQ instead
of the refund policy), and the agent then answers based on that irrelevant context.

    python examples/bad_retrieval/main.py
    agent-replay show latest
"""

from agent_replay import event, trace


def mock_retriever(query: str) -> list[dict]:
    """Returns off-task chunks with low relevance scores."""
    return [
        {"id": "doc-12", "score": 0.31, "text": "Standard shipping takes 3-5 business days."},
        {"id": "doc-30", "score": 0.27, "text": "Gift wrapping is available at checkout."},
    ]


def mock_llm_answer(query: str, context: list[dict]) -> dict:
    return {
        "role": "assistant",
        "content": "Refunds usually take 3-5 business days.",  # wrong: derived from shipping FAQ
    }


def main() -> None:
    task = "What is our 2026 refund policy?"
    with trace("research-agent", task=task):
        results = mock_retriever(task)
        event.retrieval(name="kb.search", query=task, results=results)

        answer = mock_llm_answer(task, results)
        event.llm_call(
            provider="openai",
            model="gpt-5.5",
            input_messages=[
                {"role": "user", "content": task},
                {"role": "system", "content": str(results)},
            ],
            output_message=answer,
            usage={"input_tokens": 210, "output_tokens": 22},
        )

    print("Recorded a run with bad retrieval. Try:  agent-replay show latest")


if __name__ == "__main__":
    main()
