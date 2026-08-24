"""Minimal happy-path agent, traced with Agent Replay.

Uses a mock LLM + mock tool so it runs anywhere with no API keys. It records:
llm_call -> tool_call -> llm_call (final answer).

Run it, then inspect:

    python examples/minimal_openai_agent/main.py
    agent-replay show latest
"""

from agent_replay import event, trace


def mock_llm(messages: list[dict]) -> dict:
    """Pretend to be a model deciding to call a search tool."""
    return {
        "role": "assistant",
        "content": "I'll look up the pricing page.",
        "tool_calls": [{"name": "browser.search", "arguments": {"query": "pricing page"}}],
    }


def browser_search(query: str) -> dict:
    """A mock read-only tool."""
    return {"url": "https://example.com/pricing", "title": "Pricing — Example"}


def main() -> None:
    with trace("minimal-agent", task="Find the pricing page URL"):
        messages = [{"role": "user", "content": "Find the pricing page URL"}]

        decision = mock_llm(messages)
        event.llm_call(
            provider="openai",
            model="gpt-5.5",
            input_messages=messages,
            output_message=decision,
            usage={"input_tokens": 42, "output_tokens": 18},
        )

        call = decision["tool_calls"][0]
        result = browser_search(**call["arguments"])
        event.tool_call(name=call["name"], input=call["arguments"], output=result)

        final = {"role": "assistant", "content": f"The pricing page is {result['url']}"}
        event.llm_call(
            provider="openai",
            model="gpt-5.5",
            input_messages=messages + [decision, {"role": "tool", "content": str(result)}],
            output_message=final,
            usage={"input_tokens": 90, "output_tokens": 20},
        )

    print("Recorded a run. Inspect it with:  agent-replay show latest")


if __name__ == "__main__":
    main()
