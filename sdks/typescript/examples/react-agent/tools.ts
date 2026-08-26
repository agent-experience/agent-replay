/** Four small, local tools for the demo agent. Deterministic, no network. */

export type ToolResult = { output: unknown; error: string | null };

const FACTS: Record<string, string> = {
  "capital of france": "Paris",
  "capital of japan": "Tokyo",
  "capital of italy": "Rome",
};

const WEATHER: Record<string, { condition: string; temp_f: number }> = {
  paris: { condition: "cloudy", temp_f: 59 },
  london: { condition: "rainy", temp_f: 54 },
  tokyo: { condition: "clear", temp_f: 72 },
};

/** Evaluate a simple arithmetic expression safely (digits, + - * / ( ) . and spaces only). */
function calculator(input: { expression?: string }): ToolResult {
  const expr = String(input.expression ?? "");
  if (!/^[\d+\-*/().\s]+$/.test(expr)) {
    return { output: null, error: `unsafe or invalid expression: ${expr}` };
  }
  try {
    // eslint-disable-next-line no-new-func -- input is constrained to arithmetic by the regex above.
    const result = Function(`"use strict"; return (${expr});`)();
    return { output: { expression: expr, result }, error: null };
  } catch {
    return { output: null, error: `could not evaluate: ${expr}` };
  }
}

function knowledgeLookup(input: { query?: string }): ToolResult {
  const query = String(input.query ?? "").toLowerCase().trim();
  const answer = FACTS[query];
  return { output: { query, answer: answer ?? null, found: Boolean(answer) }, error: null };
}

function getWeather(input: { city?: string }): ToolResult {
  const city = String(input.city ?? "").toLowerCase().trim();
  const hit = WEATHER[city];
  if (!hit) return { output: null, error: `no weather station found for '${input.city}'` };
  return { output: { city: input.city, condition: hit.condition, temp_f: hit.temp_f }, error: null };
}

function syncAccount(input: Record<string, unknown>): ToolResult {
  return { output: { account: input.account ?? null, status: "synced" }, error: null };
}

const DISPATCH: Record<string, (input: any) => ToolResult> = {
  calculator,
  knowledge_lookup: knowledgeLookup,
  get_weather: getWeather,
  sync_account: syncAccount,
};

export function runTool(name: string, input: unknown): ToolResult {
  const fn = DISPATCH[name];
  if (!fn) return { output: null, error: `unknown tool: ${name}` };
  return fn(input as Record<string, unknown>);
}
