/**
 * Entry point: run the demo agent, write the trace JSON, and print the exact Agent Replay
 * commands to analyze it.
 *
 *   node --experimental-strip-types run.ts                      # default "happy" scenario
 *   node --experimental-strip-types run.ts --scenario buggy     # a debuggable failure
 *   node --experimental-strip-types run.ts --scenario redaction # secrets in a tool input
 *   node --experimental-strip-types run.ts "What is 12% of 350?" # free-form question
 */
import { runAgent } from "./agent.ts";
import type { Scenario } from "./llm.ts";

const CANNED: Record<Scenario, string> = {
  happy: "What is 15% of 240, and what is the capital of France?",
  buggy: "What's the current weather in Zzyzx?",
  redaction: "Sync the Acme account.",
};

function parseArgs(argv: string[]): { scenario: Scenario; question: string; out: string } {
  let scenario: Scenario | null = null;
  let question: string | null = null;
  let out = "trace.json";
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--scenario") scenario = argv[++i] as Scenario;
    else if (a === "--out" || a === "-o") out = argv[++i];
    else if (!a.startsWith("-")) question = a;
  }
  if (!scenario) scenario = question ? "happy" : "happy";
  if (!(scenario in CANNED)) {
    console.error(`Unknown scenario '${scenario}'. Choose one of: ${Object.keys(CANNED).join(", ")}`);
    process.exit(2);
  }
  return { scenario, question: question ?? CANNED[scenario], out };
}

const { scenario, question, out } = parseArgs(process.argv.slice(2));
const { runId, answer, tracePath } = await runAgent(question, scenario, out);

console.log(`\n[mock] research-agent`);
console.log(`Q: ${question}`);
console.log(`A: ${answer}\n`);
console.log(`Wrote trace ${runId} to ${tracePath}. Analyze it with Agent Replay:`);
console.log(`  agent-replay import ${tracePath}`);
console.log(`  agent-replay show latest`);
console.log(`  agent-replay analyze latest`);
console.log(`  agent-replay stats`);
console.log(`  agent-replay sanitize latest -o run.sanitized.json`);
