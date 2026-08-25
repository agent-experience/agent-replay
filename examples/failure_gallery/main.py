"""Failure gallery: one recorded trace per taxonomy failure type (whitepaper §8.2).

Each run is tagged with ``failure_type`` metadata and is crafted so the matching Phase 2
detector fires. Record them, then analyze:

    python examples/failure_gallery/main.py
    agent-replay analyze latest
    agent-replay stats

The three standalone examples (failed_tool_call, bad_retrieval, ignored_tool_result) cover
the most common cases in more realistic detail; this gallery guarantees every failure type
has at least one runnable example trace.
"""

from agent_replay import event, trace
from agent_replay.analysis import taxonomy as t


def hallucinated_tool_argument() -> None:
    event.tool_call(
        name="crm.update_customer",
        input={"customer_id": "C-1", "refund_status": "approved"},
        output={"error": "field refund_status is deprecated"},
        error="field refund_status is deprecated",
    )


def ignored_tool_result() -> None:
    event.tool_call(
        name="ticketing.update",
        input={"ticket": "T-9"},
        output={"error": "ticket is locked"},
        error="ticket is locked",
    )
    event.llm_call(
        provider="openai",
        model="gpt-5.5",
        input_messages=[{"role": "tool", "content": "ticket is locked"}],
        output_message={"role": "assistant", "content": "Done — I closed the ticket."},
    )


def bad_retrieval() -> None:
    event.retrieval(
        name="kb.search",
        query="2026 refund policy",
        results=[{"id": "doc-12", "score": 0.31, "text": "Shipping takes 3-5 days."}],
    )


def stale_memory() -> None:
    event.memory_read(key="pricing_tier", value="legacy")
    event.tool_call(name="quote.build", input={"tier": "legacy"}, output={"ok": True})
    event.memory_write(key="pricing_tier", value="2026-standard")


def context_pollution() -> None:
    event.retrieval(
        name="kb.search",
        query="refund policy",
        results=[{"id": "doc-99", "score": 0.22, "text": "gift wrapping details"}],
    )
    event.llm_call(
        provider="openai",
        model="gpt-5.5",
        input_messages=[{"role": "system", "content": "context: gift wrapping details"}],
        output_message={"role": "assistant", "content": "..."},
    )


def excessive_retry() -> None:
    for attempt in range(3):
        event.tool_call(
            name="payments.charge",
            input={"attempt": attempt},
            output={"error": "timeout"},
            error="timeout",
        )


def loop_detected() -> None:
    for _ in range(3):
        event.llm_call(
            provider="openai",
            model="gpt-5.5",
            input_messages=[{"role": "user", "content": "same thought"}],
            output_message={"role": "assistant", "content": "same plan"},
        )


def unsafe_write_action() -> None:
    event.tool_call(name="db.delete_record", input={"id": "R-1"}, output={"ok": True})


def permission_mismatch() -> None:
    event.tool_call(name="crm.delete_customer", input={"id": "C-1"}, output={"ok": True})


def final_answer_conflict() -> None:
    event.tool_call(
        name="order.refund",
        input={"order": "O-1"},
        output={"error": "refund window expired"},
        error="refund window expired",
    )
    event.llm_call(
        provider="openai",
        model="gpt-5.5",
        input_messages=[{"role": "user", "content": "refund it"}],
        output_message={"role": "assistant", "content": "Your refund was successful."},
    )


# (failure_type, body, extra run metadata) — body runs inside an open trace.
GALLERY = [
    (t.HALLUCINATED_TOOL_ARGUMENT, hallucinated_tool_argument, {}),
    (t.IGNORED_TOOL_RESULT, ignored_tool_result, {}),
    (t.BAD_RETRIEVAL, bad_retrieval, {}),
    (t.STALE_MEMORY, stale_memory, {}),
    (t.CONTEXT_POLLUTION, context_pollution, {}),
    (t.EXCESSIVE_RETRY, excessive_retry, {}),
    (t.LOOP_DETECTED, loop_detected, {}),
    (t.UNSAFE_WRITE_ACTION, unsafe_write_action, {}),
    (t.PERMISSION_MISMATCH, permission_mismatch, {"allowed_tools": ["docs.read"]}),
    (t.FINAL_ANSWER_CONFLICT, final_answer_conflict, {}),
]


def main() -> None:
    for failure_type, body, meta in GALLERY:
        with trace("gallery", task=failure_type, failure_type=failure_type, **meta):
            body()
    print(f"Recorded {len(GALLERY)} failure traces. Try:  agent-replay stats")


if __name__ == "__main__":
    main()
