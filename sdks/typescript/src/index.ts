/**
 * @agent-replay/record — the TypeScript recorder SDK.
 *
 * This is the "TypeScript-second" SDK from the whitepaper (§11.2): a thin *producer* of trace
 * events. It records exactly the same trace format as the Python SDK and writes it as JSON.
 * You then hand that JSON to the Python tool:
 *
 *     agent-replay import trace.json
 *     agent-replay analyze latest
 *
 * All the analysis — the failure detectors, `show`, `replay`, `stats` — lives once, in the
 * Python engine, and works on any trace regardless of which language recorded it. This package
 * has ZERO runtime dependencies; it only touches `node:crypto` and `node:fs`.
 *
 * The on-disk shape mirrors agent_replay/schema.py (SCHEMA_VERSION "0.1").
 */
import { randomBytes } from "node:crypto";
import { writeFileSync } from "node:fs";

/** Bump when the trace shape changes in a breaking way — kept in lockstep with the Python schema. */
export const SCHEMA_VERSION = "0.1";

export type StepType = "llm_call" | "tool_call" | "retrieval" | "memory_read" | "memory_write";
export type RunStatus = "running" | "success" | "failed";

export interface Step {
  step_id: string;
  run_id: string;
  type: StepType;
  name?: string | null;
  input?: unknown;
  output?: unknown;
  state_before?: unknown;
  state_after?: unknown;
  error?: string | null;
  usage?: Record<string, unknown> | null;
  parent_step_id?: string | null;
  timestamp?: string | null;
  metadata?: Record<string, unknown>;
}

export interface Run {
  run_id: string;
  agent_name: string;
  task?: string | null;
  started_at?: string | null;
  ended_at?: string | null;
  status: RunStatus;
  cost_usd?: number | null;
  latency_ms?: number | null;
  metadata?: Record<string, unknown>;
  schema_version?: string;
}

/** The exact object `agent-replay import` (and `export --format json`) accepts. */
export interface TraceDocument {
  schema_version: string;
  run: Run;
  steps: Step[];
}

/** The four step fields that may carry sensitive payloads (matches Python SENSITIVE_KEYS). */
export interface SensitiveFields {
  input?: unknown;
  output?: unknown;
  state_before?: unknown;
  state_after?: unknown;
}

/** A redaction hook: receives the sensitive fields of a step, returns a scrubbed copy. */
export type RedactHook = (fields: SensitiveFields) => SensitiveFields;

export interface TraceOptions {
  /** Agent name, e.g. "research-agent". */
  agent: string;
  /** The task / user request this run is handling. */
  task?: string;
  /** Optional record-time redaction hook (see `scrub` + `DEFAULT_SECRET_PATTERNS`). */
  redact?: RedactHook;
  /** Arbitrary run-level metadata (mode, environment, etc.). */
  metadata?: Record<string, unknown>;
}

function nowIso(): string {
  // ISO-8601 ending in "Z", matching agent_replay.schema.utc_now_iso().
  return new Date().toISOString();
}

function newRunId(): string {
  return `run_${randomBytes(6).toString("hex")}`;
}

/**
 * A single agent run. Create one, record steps as they happen, then `write()` the JSON.
 *
 * Recorder methods never throw on bad input and never call your model/tools — they only
 * append a step, exactly like the Python `event.*` no-op-safe recorders.
 */
export class Trace {
  readonly run: Run;
  readonly steps: Step[] = [];
  private stepCount = 0;
  private readonly redact?: RedactHook;
  private readonly startedMs: number;

  constructor(opts: TraceOptions) {
    this.redact = opts.redact;
    this.startedMs = Date.now();
    this.run = {
      run_id: newRunId(),
      agent_name: opts.agent,
      task: opts.task ?? null,
      started_at: nowIso(),
      status: "running",
      metadata: opts.metadata ?? {},
      schema_version: SCHEMA_VERSION,
    };
  }

  get runId(): string {
    return this.run.run_id;
  }

  private record(
    type: StepType,
    fields: SensitiveFields,
    extra: { name?: string | null; error?: string | null; usage?: Record<string, unknown> | null; metadata?: Record<string, unknown> } = {},
  ): Step {
    this.stepCount += 1;
    const scrubbed = this.redact ? this.redact(fields) : fields;
    const step: Step = {
      step_id: `${type}_${this.stepCount}`,
      run_id: this.run.run_id,
      type,
      name: extra.name ?? null,
      input: scrubbed.input ?? null,
      output: scrubbed.output ?? null,
      state_before: scrubbed.state_before ?? null,
      state_after: scrubbed.state_after ?? null,
      error: extra.error ?? null,
      usage: extra.usage ?? null,
      parent_step_id: null,
      timestamp: nowIso(),
      metadata: extra.metadata ?? {},
    };
    this.steps.push(step);
    return step;
  }

  /** Record one model turn. `outputMessage` should be `{ role, content }` so text detectors can read it. */
  llmCall(args: {
    provider: string;
    model: string;
    inputMessages?: unknown;
    outputMessage?: unknown;
    usage?: Record<string, unknown> | null;
    error?: string | null;
    metadata?: Record<string, unknown>;
  }): Step {
    return this.record(
      "llm_call",
      { input: { provider: args.provider, model: args.model, messages: args.inputMessages ?? null }, output: args.outputMessage ?? null },
      { name: args.model, error: args.error, usage: args.usage, metadata: args.metadata },
    );
  }

  /** Record one tool invocation. Pass tool failures through `error` so the detectors can see them. */
  toolCall(args: {
    name: string;
    input?: unknown;
    output?: unknown;
    error?: string | null;
    stateBefore?: unknown;
    stateAfter?: unknown;
    metadata?: Record<string, unknown>;
  }): Step {
    return this.record(
      "tool_call",
      { input: args.input ?? null, output: args.output ?? null, state_before: args.stateBefore ?? null, state_after: args.stateAfter ?? null },
      { name: args.name, error: args.error, metadata: args.metadata },
    );
  }

  /** Record a retrieval / search step. */
  retrieval(args: { name: string; query?: unknown; results?: unknown; error?: string | null }): Step {
    return this.record("retrieval", { input: { query: args.query ?? null }, output: { results: args.results ?? null } }, { name: args.name, error: args.error });
  }

  /** Finalize the run: set status, ended_at, and latency_ms. Idempotent. */
  end(status: RunStatus = "success"): void {
    this.run.status = status;
    this.run.ended_at = nowIso();
    this.run.latency_ms = Date.now() - this.startedMs;
  }

  /** The canonical trace document — exactly what `agent-replay import` accepts. */
  toJSON(): TraceDocument {
    if (this.run.status === "running") this.end("success");
    return { schema_version: SCHEMA_VERSION, run: this.run, steps: this.steps };
  }

  /** Write the trace JSON to `path` (defaults to ./trace.json). Returns the path. */
  write(path = "trace.json"): string {
    writeFileSync(path, JSON.stringify(this.toJSON(), null, 2), "utf-8");
    return path;
  }
}

/**
 * Context-manager-style helper mirroring Python's `with trace(...) as run:`.
 *
 * Opens a run, runs `fn`, marks the run `success` (or `failed` if `fn` throws), writes the JSON
 * to `out` if given, and returns the run id, your function's result, and the Trace.
 */
export async function trace<T>(
  opts: TraceOptions & { out?: string },
  fn: (t: Trace) => Promise<T> | T,
): Promise<{ runId: string; result: T; trace: Trace }> {
  const t = new Trace(opts);
  try {
    const result = await fn(t);
    t.end("success");
    return { runId: t.runId, result, trace: t };
  } catch (err) {
    t.end("failed");
    throw err;
  } finally {
    if (opts.out) t.write(opts.out);
  }
}

// ---------------------------------------------------------------------------------------------
// Redaction — a faithful port of agent_replay/redaction.py's scrub() + DEFAULT_SECRET_PATTERNS.
// ---------------------------------------------------------------------------------------------

/** Common secret-bearing key globs (same set as the Python SDK). Case-insensitive. */
export const DEFAULT_SECRET_PATTERNS: readonly string[] = [
  "*password*",
  "*passwd*",
  "*secret*",
  "*token*",
  "*api_key*",
  "*apikey*",
  "*access_key*",
  "*credential*",
  "authorization",
  "cookie",
  "*ssn*",
];

const REDACTED = "«redacted»"; // «redacted» — identical marker to the Python SDK.

function globToRegExp(glob: string): RegExp {
  // Translate an fnmatch-style glob (`*`) to an anchored, case-insensitive RegExp.
  const escaped = glob.replace(/[.+^${}()|[\]\\]/g, "\\$&").replace(/\*/g, ".*").replace(/\?/g, ".");
  return new RegExp(`^${escaped}$`, "i");
}

function keyMatches(key: string, patterns: readonly string[]): boolean {
  return patterns.some((p) => globToRegExp(p).test(key));
}

/**
 * Recursively replace values whose key matches one of `patterns` with «redacted».
 * Mirrors agent_replay.redaction.scrub — safe to use as (part of) a `redact` hook.
 */
export function scrub(value: unknown, patterns: readonly string[] = DEFAULT_SECRET_PATTERNS): unknown {
  if (patterns.length === 0) return value;
  if (Array.isArray(value)) return value.map((v) => scrub(v, patterns));
  if (value && typeof value === "object") {
    const out: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(value as Record<string, unknown>)) {
      out[k] = keyMatches(k, patterns) ? REDACTED : scrub(v, patterns);
    }
    return out;
  }
  return value;
}
