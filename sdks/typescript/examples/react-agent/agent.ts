/**
 * A classic ReAct loop — and the ~6 lines of Agent Replay instrumentation that make it
 * debuggable. `trace(...)` opens a run; every model turn is recorded with `llmCall` and every
 * tool with `toolCall`. That's the whole integration; the analysis happens later, in the
 * Python `agent-replay` tool, on the JSON this writes.
 */
import { DEFAULT_SECRET_PATTERNS, scrub, trace } from "../../src/index.ts";
import { complete, type Scenario, type ToolOutcome } from "./llm.ts";
import { runTool } from "./tools.ts";

const MAX_STEPS = 6;

// A record-time redaction hook, same idea as the Python demo's trace(redact=...). We extend the
// built-in secret globs with app-specific PII keys (e.g. *email*) so nothing sensitive is ever
// written to the trace.
const REDACT_PATTERNS = [...DEFAULT_SECRET_PATTERNS, "*email*", "customer_id"];
const redact = (fields: Record<string, unknown>) =>
  Object.fromEntries(Object.entries(fields).map(([k, v]) => [k, scrub(v, REDACT_PATTERNS)]));

export interface AgentResult {
  runId: string;
  answer: string;
  tracePath: string;
}

export async function runAgent(
  question: string,
  scenario: Scenario,
  out: string,
): Promise<AgentResult> {
  let answer = "";
  const { runId } = await trace(
    { agent: "research-agent", task: question, redact, metadata: { mode: "mock" }, out },
    async (run) => {
      const results: ToolOutcome[] = [];
      for (let round = 0; round < MAX_STEPS; round++) {
        const r = complete(question, round, results, scenario);
        run.llmCall({
          provider: "mock",
          model: "mock:claude-sonnet-5",
          inputMessages: [{ role: "user", content: question }],
          // Canonical assistant-message shape so Agent Replay's text detectors can read the answer.
          outputMessage: { role: "assistant", content: r.text, tool_calls: r.toolCalls },
          usage: r.usage,
        });
        answer = r.text || answer;
        if (r.toolCalls.length === 0) break; // no tools requested → final answer

        for (const call of r.toolCalls) {
          const { output, error } = runTool(call.name, call.input);
          run.toolCall({ name: call.name, input: call.input, output, error }); // pass errors through
          results.push({ name: call.name, output, error });
        }
      }
      return answer;
    },
  );
  return { runId, answer, tracePath: out };
}
