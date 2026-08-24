import json

from agent_replay import event, trace
from agent_replay.exporters import export_run, export_run_otlp


def _record(store):
    with trace("agent-a", task="t", store=store) as run:
        event.llm_call(
            provider="openai",
            model="gpt-5.5",
            input_messages=[{"role": "user", "content": "hi"}],
            output_message={"role": "assistant", "content": "yo"},
            usage={"input_tokens": 10, "output_tokens": 3},
        )
        event.tool_call(name="crm.update", input={"x": 1}, output={"error": "bad"}, error="bad")
    return store.get_run(run.run_id), store.get_steps(run.run_id)


def test_json_export_shape_and_serializable(store):
    run, steps = _record(store)
    payload = export_run(run, steps)
    assert payload["schema_version"] == "0.1"
    assert payload["run"]["run_id"] == run.run_id
    assert len(payload["steps"]) == 2
    json.dumps(payload)  # must be serializable


def test_otlp_export_shape(store):
    run, steps = _record(store)
    otlp = export_run_otlp(run, steps)
    json.dumps(otlp)
    spans = otlp["resourceSpans"][0]["scopeSpans"][0]["spans"]
    # one root span + one span per step
    assert len(spans) == 1 + len(steps)
    root = spans[0]
    assert root["traceId"] and root["spanId"]
    # every step span shares the trace id and is parented to the root span
    for span in spans[1:]:
        assert span["traceId"] == root["traceId"]
        assert span["parentSpanId"] == root["spanId"]

    # GenAI attributes present on the llm span
    llm_span = spans[1]
    keys = {a["key"]: a["value"] for a in llm_span["attributes"]}
    assert keys["gen_ai.system"]["stringValue"] == "openai"
    assert keys["gen_ai.request.model"]["stringValue"] == "gpt-5.5"
    assert keys["gen_ai.usage.input_tokens"]["intValue"] == "10"

    # error step maps to OTLP status ERROR (code 2)
    tool_span = spans[2]
    assert tool_span["status"]["code"] == 2
