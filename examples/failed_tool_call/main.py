"""Failure example: hallucinated tool argument.

The agent calls ``crm.update_customer`` with a field (``refund_status``) that no longer
exists in the CRM schema. The tool returns an error, but this example records the full
trajectory so a developer (and, in Phase 2, an automatic detector) can see the mismatch.

    python examples/failed_tool_call/main.py
    agent-replay show latest
"""

from agent_replay import event, trace


def mock_llm_decide(messages: list[dict]) -> dict:
    return {
        "role": "assistant",
        "content": "Approving the refund by updating the CRM.",
        "tool_calls": [
            {
                "name": "crm.update_customer",
                "arguments": {"customer_id": "C-1827", "refund_status": "approved"},
            }
        ],
    }


def crm_update_customer(customer_id: str, **fields) -> dict:
    """Mock CRM: 'refund_status' is a deprecated/nonexistent field."""
    valid_fields = {"email", "name", "tier"}
    unknown = set(fields) - valid_fields
    if unknown:
        return {"error": f"field {sorted(unknown)[0]} is deprecated"}
    return {"ok": True}


def main() -> None:
    with trace("customer-support-agent", task="Refund this order if eligible"):
        messages = [{"role": "user", "content": "Refund order O-42 if eligible"}]

        decision = mock_llm_decide(messages)
        event.llm_call(
            provider="openai",
            model="gpt-5.5",
            input_messages=messages,
            output_message=decision,
            usage={"input_tokens": 120, "output_tokens": 30},
        )

        call = decision["tool_calls"][0]
        result = crm_update_customer(**call["arguments"])
        event.tool_call(
            name=call["name"],
            input=call["arguments"],
            output=result,
            error=result.get("error"),
        )

    print("Recorded a run with a hallucinated tool argument. Try:  agent-replay show latest")


if __name__ == "__main__":
    main()
