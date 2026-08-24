"""Failure example: ignored tool result.

A tool returns an error, but the agent continues as if it had succeeded and reports success
to the user. The trace makes the contradiction between the tool output and the final answer
visible.

    python examples/ignored_tool_result/main.py
    agent-replay show latest
"""

from agent_replay import event, trace


def ticketing_update(ticket: str, status: str) -> dict:
    """Mock ticketing tool that rejects the update."""
    return {"error": "ticket is locked and cannot be modified"}


def mock_llm_final(tool_result: dict) -> dict:
    # The agent ignores the error and claims success anyway.
    return {"role": "assistant", "content": "Done — I've closed ticket T-9 for you."}


def main() -> None:
    with trace("support-agent", task="Close ticket T-9"):
        result = ticketing_update(ticket="T-9", status="closed")
        event.tool_call(
            name="ticketing.update",
            input={"ticket": "T-9", "status": "closed"},
            output=result,
            error=result.get("error"),
        )

        final = mock_llm_final(result)
        event.llm_call(
            provider="openai",
            model="gpt-5.5",
            input_messages=[{"role": "tool", "content": str(result)}],
            output_message=final,
            usage={"input_tokens": 60, "output_tokens": 16},
        )

    print("Recorded a run that ignored a tool error. Try:  agent-replay show latest")


if __name__ == "__main__":
    main()
