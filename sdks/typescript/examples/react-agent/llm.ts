/**
 * A deterministic, scripted "model" so the demo runs with no API key and no network — the same
 * approach as the Python demo. Each scenario drives a fixed tool-use plan so a given scenario
 * always triggers the same Agent Replay findings.
 */

export interface ToolCall {
  id: string;
  name: string;
  input: Record<string, unknown>;
}

export interface LlmResponse {
  text: string;
  toolCalls: ToolCall[];
  usage: { input_tokens: number; output_tokens: number };
}

export type Scenario = "happy" | "buggy" | "redaction";

export interface ToolOutcome {
  name: string;
  output: unknown;
  error: string | null;
}

const PERCENT = /(\d+(?:\.\d+)?)\s*%\s*of\s*(\d+(?:\.\d+)?)/i;
const CAPITAL = /capital of ([a-zA-Z]+)/i;
const WEATHER_IN = /weather (?:in|for) ([a-zA-Z .]+?)(?:[?.!]|$)/i;

function resp(text: string, toolCalls: ToolCall[] = []): LlmResponse {
  return { text, toolCalls, usage: { input_tokens: 60, output_tokens: text ? 25 : 15 } };
}

let counter = 0;
function call(name: string, input: Record<string, unknown>): ToolCall {
  counter += 1;
  return { id: `toolu_mock_${counter}`, name, input };
}

/** The scripted model. `round` is the number of tool-result rounds already returned. */
export function complete(
  question: string,
  round: number,
  results: ToolOutcome[],
  scenario: Scenario,
): LlmResponse {
  if (scenario === "buggy") {
    if (round === 0) {
      const m = WEATHER_IN.exec(question);
      const city = m ? m[1].trim() : "Zzyzx";
      return resp("Let me check the weather.", [call("get_weather", { city })]);
    }
    // The bug: ignore the tool error and confidently claim success.
    return resp("Done! It's currently sunny and about 72°F there right now.");
  }

  if (scenario === "redaction") {
    if (round === 0) {
      return resp("Syncing the account.", [
        call("sync_account", {
          account: "acme",
          api_key: "sk-live-DEMO-abc123",
          token: "ghp_DEMO_secret_xyz",
          customer_email: "ceo@acme.example",
        }),
      ]);
    }
    return resp("All set — I've synced the Acme account.");
  }

  // happy / free-form
  if (round === 0) {
    const calls: ToolCall[] = [];
    const pm = PERCENT.exec(question);
    if (pm) calls.push(call("calculator", { expression: `${pm[2]} * ${pm[1]} / 100` }));
    const cm = CAPITAL.exec(question);
    if (cm) calls.push(call("knowledge_lookup", { query: `capital of ${cm[1]}` }));
    if (calls.length) return resp("Let me gather the facts.", calls);
    return resp("I don't have a tool for that, but here's my best general answer.");
  }

  const parts: string[] = [];
  for (const r of results) {
    if (r.error) continue;
    const o = r.output as Record<string, any>;
    if (r.name === "calculator") parts.push(`the calculation gives ${o.result}`);
    else if (r.name === "knowledge_lookup" && o.answer) parts.push(String(o.answer));
    else if (r.name === "get_weather") parts.push(`${o.city} is ${o.condition}, ${o.temp_f}°F`);
  }
  return resp(parts.length ? `Here's what I found: ${parts.join("; ")}.` : "I couldn't find that.");
}
