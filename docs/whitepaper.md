# Agent Replay: A Time-Travel Debugging and Experience Memory Platform for AI Agents

**Version**: v0.1  
**Date**: August 24, 2026  
**Positioning**: Research-informed open-source developer tool  
**One-line definition**: Agent Replay is a local-first debugging layer for AI agents that records agent execution traces, helps developers identify failures, replay or fork execution from any step, and eventually convert successful and failed trajectories into reusable experience memory.

---

## 1. Executive Summary

AI agents are evolving from simple single-call LLM applications into complex software systems involving multi-step reasoning, tool calls, memory reads/writes, external environment interaction, long-running tasks, and sometimes parallel sub-agents.

Traditional observability can tell developers **what happened**, but it does not fully answer the most important questions in agent development:

> Why did this agent fail?  
> Can I return to the failure point and rerun from there?  
> Would the run succeed if I changed the prompt, model, retriever, tool output, or memory state?  
> Can I extract reusable lessons from successful and failed runs so future agents perform better?

This project proposes **Agent Replay**: a **time-travel debugging layer for AI agents**.

The roadmap has four phases:

1. **Trace + Replay**: Record agent execution traces and support local playback.
2. **Failure Analysis + Eval**: Automatically identify agent failure modes and likely root causes.
3. **Checkpoint + Fork**: Fork execution from any step and compare alternative branches.
4. **Experience Memory**: Extract reusable experience from past trajectories and feed it into future agent runs.

The first implementation should be **Python-first** and **TypeScript-second**, because most agent developers currently build in those ecosystems. Go and Rust should not be the first SDK entry points; they are better suited for later-stage collectors, daemons, replay engines, sandbox sidecars, and performance-sensitive infrastructure.

---

## 2. Background and Problem Definition

### 2.1 Agent Execution Is Not a Normal API Request

A traditional backend request usually looks like this:

```text
request → business logic → database / external API → response
```

An AI agent run looks more like this:

```text
task
  → model reasoning
  → tool selection
  → tool call
  → environment feedback
  → memory read/write
  → retry / reflection / branch
  → final action
```

The ReAct paper formalized the pattern of interleaving reasoning traces and task-specific actions. Reasoning helps the model update plans and handle exceptions; actions allow the model to interact with external knowledge sources, tools, or environments.

This implies that agent observability cannot merely record prompts and responses. It must capture:

```text
reasoning
action selection
tool invocation
tool result
environment observation
memory access
state transition
failure and retry behavior
```

### 2.2 Agent Failure Is a Core Development Problem

Agent failure is not an edge case. It is one of the central problems in agent engineering.

AgentBench evaluates LLM-as-Agent systems across multiple interactive environments and highlights long-horizon reasoning, decision-making, and instruction-following as major challenges. WebArena shows that even strong LLM-based agents struggle on realistic web tasks, where end-to-end success rates remain far below human performance.

This suggests that the core need is not just a prettier dashboard. Agent developers need systematic support for:

```text
failure localization
failure reproduction
branch comparison
alternative execution testing
long-term experience accumulation
```

### 2.3 Traditional Observability Is Necessary but Not Sufficient

OpenTelemetry is already moving toward GenAI semantic conventions, including spans for GenAI calls, tools, and agent frameworks. That is a strong signal that GenAI and agent telemetry are becoming infrastructure-level concerns.

However, telemetry mostly answers:

> What happened?

Agent Replay should answer a more powerful question:

> What would have happened if we changed the decision at step N?

Therefore, this project should not position itself as a replacement for OpenTelemetry. Instead, it should build an agent-specific debugging primitive on top of standard telemetry concepts:

```text
Trace → Inspect → Replay → Fork → Evaluate → Learn
```

---

## 3. Project Positioning

### 3.1 Tagline

> **Time-travel debugging for AI agents.**

### 3.2 Product Definition

Agent Replay is a local-first, self-hostable, open-source-first debugging and experience-learning tool for AI agents.

It helps developers:

- record structured traces of every agent run;
- inspect LLM calls, tool calls, retrieval events, memory events, and state transitions;
- replay or fork execution from failure points;
- compare outcomes across different prompts, models, tools, retrievers, and memory states;
- identify common agent failure modes;
- convert successful and failed trajectories into reusable experience memory.

### 3.3 Non-Goals for the Initial Version

The first version should not attempt to build:

- a full SaaS observability platform;
- a generic vector database;
- a complete Agent OS;
- OS-level deterministic replay;
- a distributed sandbox runtime;
- enterprise-grade SAML, RBAC, billing, or long-term retention management.

---

## 4. Research and Technical Grounding

### 4.1 Reasoning + Acting

**ReAct** provides the foundational abstraction for agent traces. Agents are not just single-step model calls; they are trajectories where reasoning and acting are interleaved.

Implication for Agent Replay:

```text
Agent traces must capture:
- reasoning steps
- action selection
- tool calls
- observations
- plan updates
- exception handling
```

### 4.2 Agent Evaluation

**AgentBench** supports the need for multi-environment, multi-step evaluation of agents. It shows that failures often arise from long-horizon reasoning, decision-making, and instruction-following issues.

**WebArena** supports the claim that real-world agent tasks are hard. Web agents fail frequently in realistic browser-based tasks, making debugging and replay critical.

**SWE-bench Verified** is relevant for future coding-agent use cases, especially where replay and failure diagnosis can help developers understand why an agent did or did not fix a real software issue.

### 4.3 Reflection and Experience Learning

**Reflexion** shows that language agents can improve through verbal reinforcement and reflection over previous attempts.

**ExpeL** is directly aligned with this project’s long-term direction: agents can improve by accumulating experience from past interactions.

**Voyager** demonstrates lifelong learning through environment feedback, skill libraries, and iterative self-improvement.

These works support Phase 4:

```text
execution trace → reflection → reusable experience → future performance improvement
```

### 4.4 Long-Term Memory

**Generative Agents** introduced memory streams, reflection, and planning mechanisms for agents that maintain continuity across interactions.

**MemGPT** frames the LLM context window as limited memory and proposes virtual context management across memory tiers.

Recent surveys on LLM-agent memory mechanisms also position memory as a critical capability for complex long-running agent behavior.

Agent Replay should not treat memory as merely “store text in a vector database.” Instead, memory should be evaluated based on whether it actually improves future agent behavior.

### 4.5 Record/Replay and Checkpointing Systems

The systems community has a long tradition of record/replay debugging.

Mozilla’s **rr** demonstrated that recording once and replaying deterministically can support reverse debugging, hard-to-reproduce failure analysis, and deployed-system forensics.

**CRIU** shows that Linux containers and applications can be checkpointed and restored.

**Firecracker** and related microVM snapshot work show that snapshot/restore is an important primitive for serverless and short-lived compute.

Agent Replay should borrow the spirit of these systems, but the first version should not attempt OS-level deterministic replay. It should instead implement:

> **Semantic replay for AI agents**

That means recording semantic execution steps, freezing LLM/tool/retrieval/memory inputs and outputs, and allowing developers to modify configuration or mock outputs from a selected step onward.

---

## 5. Core Technical Concepts

### 5.1 Agent Run

An **Agent Run** is one complete execution of an agent task.

Example:

```json
{
  "run_id": "run_abc123",
  "agent_name": "customer-support-agent",
  "task": "Refund this order if eligible",
  "started_at": "2026-08-24T03:00:00Z",
  "ended_at": "2026-08-24T03:00:43Z",
  "status": "failed",
  "cost_usd": 0.84,
  "latency_ms": 43200
}
```

### 5.2 Agent Step

An **Agent Step** is a meaningful state transition inside an agent run.

Example:

```json
{
  "step_id": "tool_call_4",
  "run_id": "run_abc123",
  "type": "tool_call",
  "name": "crm.update_customer",
  "input": {
    "customer_id": "C-1827",
    "refund_status": "approved"
  },
  "output": {
    "error": "field refund_status is deprecated"
  },
  "state_before": {},
  "state_after": {},
  "timestamp": "2026-08-24T03:00:21Z"
}
```

### 5.3 Replay Modes

Agent Replay should define three replay modes:

| Mode | Meaning | Initial Support |
|---|---|---|
| Playback Replay | Replay the recorded trajectory without calling models or tools again | Phase 1 |
| Mocked Replay | Freeze selected LLM/tool/retrieval outputs and rerun downstream logic | Phase 2 |
| Forked Replay | Modify prompt/model/tool/retriever config from a selected step and create a new branch | Phase 3 |

### 5.4 Experience Memory

An **Experience Memory** is a reusable lesson extracted from a historical trajectory.

Example:

```json
{
  "experience_id": "exp_001",
  "source_run_id": "run_abc123",
  "source_step_id": "tool_call_4",
  "type": "guardrail",
  "content": "Before calling crm.update_customer, verify that the target field exists in the CRM schema.",
  "applies_to": ["crm", "customer-support-agent", "write-action"],
  "confidence": 0.82,
  "evidence": {
    "failure_type": "stale_tool_schema",
    "fixed_by_run_id": "run_def456"
  }
}
```

---

## 6. Target Users and Use Cases

### 6.1 Persona A: Agent App Developer

This user builds customer support agents, research agents, CRM agents, data analysis agents, or coding agents in Python or TypeScript.

Pain points:

- agent failures are intermittent and hard to reproduce;
- tool call arguments are often wrong;
- prompt changes are difficult to evaluate;
- production traces may contain sensitive data and cannot easily be uploaded to third-party SaaS tools.

### 6.2 Persona B: AI Infrastructure Engineer

This user maintains an internal agent platform, tool registry, memory system, or execution environment.

Pain points:

- different teams report inconsistent agent failure modes;
- there is no shared trace schema;
- replay, fork, and eval pipelines are missing;
- organizational knowledge from previous agent runs is not reused.

### 6.3 Persona C: Open-Source Agent Framework Maintainer

This user maintains an agent SDK, workflow framework, or tool-use library.

Pain points:

- users report “the agent is unstable,” but issues lack reproducible traces;
- framework maintainers need standardized trace exports;
- complex agent loops are difficult to debug.

---

## 7. Phase 1: Trace + Replay

### 7.1 Goal

Build an installable, local-first agent trace recorder and playback replay tool.

Target developer experience:

```python
from agent_replay import trace

with trace("customer-support-agent"):
    result = agent.run("Refund this order if eligible")
```

CLI:

```bash
agent-replay list
agent-replay show latest
agent-replay open latest
agent-replay export latest --format json
agent-replay export latest --format otlp
```

### 7.2 MVP Scope

Phase 1 must support:

- Python SDK;
- local SQLite trace store;
- JSON trace schema;
- CLI run listing;
- CLI timeline inspection;
- LLM call event;
- tool call event;
- retrieval event;
- memory read/write event;
- playback replay;
- three examples:
  - hallucinated tool argument;
  - bad retrieval;
  - ignored tool result.

Phase 1 should not support yet:

- re-executing side-effectful external tools;
- automatic root-cause analysis;
- checkpoint/fork;
- hosted dashboard;
- distributed execution.

### 7.3 Suggested Repository Structure

```text
agent-replay/
  README.md
  pyproject.toml
  agent_replay/
    __init__.py
    trace.py
    context.py
    schema.py
    store.py
    exporters/
      json.py
      otlp.py
    cli/
      main.py
  examples/
    minimal_openai_agent/
    failed_tool_call/
    bad_retrieval/
    ignored_tool_result/
  docs/
    whitepaper.md
    research.md
    adr/
      001-agent-trace-schema.md
      002-semantic-replay.md
      003-failure-taxonomy.md
```

### 7.4 Core API

```python
from agent_replay import trace, event

with trace("research-agent", task="Find latest pricing"):
    event.llm_call(
        provider="openai",
        model="gpt-5.5",
        input_messages=[...],
        output_message={...},
        usage={"input_tokens": 1200, "output_tokens": 300}
    )

    event.tool_call(
        name="browser.search",
        input={"query": "pricing page"},
        output={"url": "https://example.com/pricing"}
    )
```

### 7.5 Phase 1 Acceptance Criteria

Phase 1 is complete when:

- [x] `pip install agent-replay` works;
- [x] a developer can run the minimal example in under 5 minutes;
- [x] a local SQLite trace store is generated;
- [x] `agent-replay list` lists previous runs;
- [x] `agent-replay show latest` displays a timeline;
- [x] LLM calls, tool calls, retrieval events, and memory events can be recorded;
- [x] traces can be exported as JSON;
- [x] traces can be exported in an OpenTelemetry-compatible format;
- [x] at least three failure examples are runnable;
- [x] the README clearly communicates “Time-travel debugging for AI agents” in the first screen;
- [x] `docs/research.md` contains key papers and standards;
- [x] all examples run in CI;
- [x] no hosted service is required.

---

## 8. Phase 2: Failure Analysis + Eval

### 8.1 Goal

Build failure analysis on top of traces and generate explainable failure reports.

Target CLI:

```bash
agent-replay analyze run_abc123
```

Example output:

```text
Likely root cause:
- Tool call used deprecated field: refund_status
- Agent ignored tool error and continued
- Suggested replay point: before tool_call_4
```

### 8.2 Failure Taxonomy

Initial built-in detectors:

| Failure Type | Description |
|---|---|
| hallucinated_tool_argument | Tool argument does not exist or does not match schema |
| ignored_tool_result | Tool returned an error, but the agent continued as if it succeeded |
| bad_retrieval | Retrieved content is poorly aligned with the task |
| stale_memory | Old memory influenced the current decision incorrectly |
| context_pollution | Context contains conflicting or irrelevant information |
| excessive_retry | Retry count is abnormally high |
| loop_detected | Agent repeats the same action pattern |
| unsafe_write_action | Agent performs a write action without validation |
| permission_mismatch | Agent attempts a tool call outside its permission scope |
| final_answer_conflict | Final answer conflicts with tool observations |

### 8.3 Eval Output

Example:

```json
{
  "run_id": "run_abc123",
  "success": false,
  "failure_types": [
    "hallucinated_tool_argument",
    "ignored_tool_result"
  ],
  "severity": "high",
  "suggested_replay_step": "tool_call_4",
  "confidence": 0.76
}
```

### 8.4 Phase 2 Acceptance Criteria

- [x] At least five deterministic detectors are implemented; *(ten, covering the full taxonomy)*
- [x] at least two LLM-assisted detector interfaces are implemented;
- [x] `agent-replay analyze <run_id>` generates a failure report;
- [x] the report includes likely root cause, evidence, and suggested replay point;
- [x] every detector has unit tests;
- [x] every failure type has an example trace; *(`examples/failure_gallery`)*
- [x] custom user-defined detectors are supported; *(`register_detector` + `--plugin`)*
- [x] analysis results can be exported as JSON; *(`analyze --format json`)*
- [x] multiple runs can be aggregated for failure statistics; *(`agent-replay stats`)*
- [x] README includes a “Find why your agent failed” demo;
- [x] `.agent-replayignore` is supported (deferred from Phase 1);
- [x] a `sanitize` command is available before export (deferred from Phase 1).

---

## 9. Phase 3: Checkpoint + Fork

### 9.1 Goal

Allow developers to fork an agent run from any step, change the prompt/model/tool/retriever/memory configuration, and compare alternative branches.

Target CLI:

```bash
agent-replay fork run_abc123 --from step_7 --patch prompt.fix.md
agent-replay diff run_abc123 run_def456
```

### 9.2 Fork Scenarios

Supported branch types:

```text
Branch A: change model
Branch B: change prompt
Branch C: change retriever config
Branch D: mock tool output
Branch E: disable memory item
```

### 9.3 Replay Strategy

Agent Replay should implement semantic replay rather than OS-level deterministic replay.

Principles:

- record each step’s input, output, state_before, and state_after;
- side-effectful tools should not be re-executed by default;
- read-only tools may be re-executed;
- external API outputs can be mocked;
- LLM calls can be either fixed-output replay or re-query;
- memory state can be replayed from a snapshot or from the current view.

### 9.4 Diff Metrics

```text
success / failure
latency
token cost
number of retries
tool error count
failure type
final output similarity
side-effect count
safety violation count
```

### 9.5 Phase 3 Acceptance Criteria

- [ ] A fork can be created from any step;
- [ ] prompt patches are supported;
- [ ] model switching is supported;
- [ ] mocked tool output is supported;
- [ ] retriever configuration patches are supported;
- [ ] memory item enable/disable is supported;
- [ ] `agent-replay diff` compares two runs;
- [ ] side-effectful tools are not automatically re-executed;
- [ ] every replay action has an audit log;
- [ ] CLI or UI can display a branch tree;
- [ ] at least three fork demos exist:
  - fixing a bad prompt;
  - replacing stale retrieval;
  - mocking a failed tool output.

---

## 10. Phase 4: Experience Memory

### 10.1 Goal

Convert historical agent traces into reusable experience memory that can be retrieved and injected into future agent runs.

Target CLI:

```bash
agent-replay extract-experience run_abc123
agent-replay memory search "CRM write action"
```

Agent usage:

```python
from agent_replay.memory import ExperienceMemory

agent = Agent(
    memory=ExperienceMemory(namespace="customer-support")
)
```

### 10.2 Experience Extraction Targets

The system should extract experience from:

```text
successful trajectories
failed trajectories
failure fixes
tool-use patterns
retrieval corrections
safety guardrails
domain-specific heuristics
```

### 10.3 Experience Lifecycle

Every experience memory should include:

```text
source trace
evidence
applicability condition
confidence
last_used_at
success_delta
decay policy
owner / namespace
```

### 10.4 Memory Quality Control

Memory must not become a garbage pile. Therefore, Phase 4 should include:

- deduplication;
- contradiction detection;
- staleness detection;
- success attribution;
- memory ablation evaluation;
- namespace isolation;
- TTL / decay;
- manual approval workflow.

### 10.5 Phase 4 Acceptance Criteria

- [ ] Experience can be extracted from a run;
- [ ] every experience contains evidence and source trace;
- [ ] experience can be retrieved by task similarity;
- [ ] future agent runs can inject relevant experience;
- [ ] manual approve/reject is supported;
- [ ] memory deduplication is supported;
- [ ] stale memory can be marked;
- [ ] memory impact evaluation is supported;
- [ ] at least one demo shows experience memory improving a later run;
- [ ] namespace isolation is supported;
- [ ] the experience library can be exported.

---

## 11. Technical Architecture

### 11.1 v0 Architecture

```text
Python Agent App
      │
      ▼
agent-replay SDK
      │
      ▼
Local Event Buffer
      │
      ▼
SQLite Trace Store
      │
      ├── CLI
      ├── JSON Exporter
      └── OTLP Exporter
```

### 11.2 v1 Architecture

```text
Python SDK         TypeScript SDK
     │                  │
     └────── Trace Events ──────┐
                                ▼
                       agent-replayd
                         Go Collector
                                │
              ┌─────────────────┼─────────────────┐
              ▼                 ▼                 ▼
          Local Store       OTLP Export       Hosted API
              │
              ▼
        Replay / Fork Engine
              │
              ▼
       Experience Memory Layer
```

### 11.3 Language Strategy

| Layer | Preferred Language | Reason |
|---|---|---|
| Python SDK | Python | Main entry point for agent and ML developers |
| TypeScript SDK | TypeScript | Strong fit for web-native agents, Next.js, and Vercel AI SDK |
| Local UI | TypeScript | Natural choice for frontend tooling |
| CLI v0 | Python | Fastest path for early iteration |
| Collector v1 | Go | Good fit for daemons, ingestion, deployment |
| Replay core v2 | Rust | Strong fit for high-performance diffing, state machines, and safety boundaries |
| Sandbox sidecar | Rust / Go | Better suited for systems-level integration |

The key principle is:

> Early-stage language choice should maximize adoption, not architectural elegance.

---

## 12. Open-Source and Commercial Strategy

### 12.1 Open-Source Scope

Recommended open-source components:

- SDK instrumentation;
- trace schema;
- local SQLite store;
- CLI;
- JSON exporter;
- OTLP-compatible exporter;
- basic replay;
- basic failure detectors;
- examples;
- research documentation.

### 12.2 Commercial Scope

Potential commercial components:

- hosted dashboard;
- team collaboration;
- trace retention and search;
- advanced root-cause analysis;
- enterprise connectors;
- branch comparison UI;
- experience memory optimization;
- approval workflow;
- compliance and audit;
- private deployment support.

### 12.3 Narrative

Do not position the project as:

```text
Another LLM observability platform
```

Position it as:

```text
Agent Replay: Time-travel debugging for AI agents
```

Long-term narrative:

```text
Observe → Debug → Replay → Fork → Learn → Improve
```

---

## 13. Recommended Roadmap

### Milestone 0: Project Setup

Target: Week 1

Deliverables:

- [ ] GitHub org / repo;
- [ ] README;
- [ ] `docs/whitepaper.md`;
- [ ] `docs/research.md`;
- [ ] trace schema draft;
- [ ] minimal package skeleton.

### Milestone 1: Python Trace MVP

Target: Weeks 2–3

Deliverables:

- [ ] Python SDK;
- [ ] trace context manager;
- [ ] event API;
- [ ] SQLite store;
- [ ] CLI list/show/export;
- [ ] minimal example.

### Milestone 2: Failure Examples

Target: Week 4

Deliverables:

- [ ] bad retrieval example;
- [ ] hallucinated tool argument example;
- [ ] ignored tool result example;
- [ ] demo GIF;
- [ ] CI examples.

### Milestone 3: Playback Replay

Target: Weeks 5–6

Deliverables:

- [ ] playback replay;
- [ ] timeline renderer;
- [ ] JSON export;
- [ ] OTLP-compatible export;
- [ ] first public release v0.1.

### Milestone 4: Failure Analysis

Target: Weeks 7–10

Deliverables:

- [ ] deterministic detectors;
- [ ] LLM-assisted detector interface;
- [ ] `analyze` command;
- [ ] failure taxonomy docs;
- [ ] batch run analysis.

### Milestone 5: Fork Prototype

Target: Weeks 11–14

Deliverables:

- [ ] prompt patch replay;
- [ ] mock tool output replay;
- [ ] branch tree;
- [ ] run diff;
- [ ] fork demo.

### Milestone 6: Experience Memory Prototype

Target: Weeks 15–20

Deliverables:

- [ ] experience extraction;
- [ ] experience store;
- [ ] experience retrieval;
- [ ] injection into future runs;
- [ ] memory impact evaluation;
- [ ] end-to-end demo.

---

## 14. Example User Stories

### User Story 1: Diagnose Tool Call Failure

As an agent developer,  
I want to see every tool call’s input, output, and error,  
so that I can determine whether the failure came from a hallucinated argument or tool schema mismatch.

Acceptance:

- [ ] trace includes tool name;
- [ ] trace includes input;
- [ ] trace includes output;
- [ ] trace includes error;
- [ ] failure detector can identify schema mismatch.

### User Story 2: Replay a Failed Trajectory

As an agent developer,  
I want to replay the full timeline of a failed run,  
so that I can understand how the agent gradually moved toward the wrong outcome.

Acceptance:

- [ ] historical run can be loaded by run_id;
- [ ] timeline is ordered by timestamp;
- [ ] every step’s input and output can be inspected;
- [ ] external APIs are not called again;
- [ ] playback matches the original recorded trace.

### User Story 3: Fork from a Failure Point

As an agent developer,  
I want to fork execution from before the failure step and modify the prompt,  
so that I can validate whether the prompt fix solves the issue.

Acceptance:

- [ ] `--from step_id` is supported;
- [ ] prompt patch is supported;
- [ ] forked run receives a new run_id;
- [ ] forked run can be diffed against the original run;
- [ ] side-effectful tools are not re-executed by default.

### User Story 4: Extract Experience Memory

As an agent platform engineer,  
I want to extract a reusable lesson from a failure fix,  
so that similar future tasks can receive the relevant guardrail before execution.

Acceptance:

- [ ] experience can be generated from a source run;
- [ ] experience records evidence;
- [ ] future runs can retrieve the experience;
- [ ] experience can be injected into prompt/context;
- [ ] success rate before and after injection can be evaluated.

---

## 15. Overall Acceptance Checklist

### 15.1 Product Acceptance

- [ ] A developer can run the minimal example within 5 minutes;
- [ ] the README explains the project value within the first screen;
- [ ] at least three high-quality demos exist;
- [ ] at least one demo shows “trace → failure → replay”;
- [ ] at least one demo shows “fork → diff”;
- [ ] at least one demo shows “trace → experience memory”;
- [ ] GitHub issue template supports sanitized trace upload;
- [ ] documentation clearly states non-goals.

### 15.2 Technical Acceptance

- [ ] SDK supports nested trace context;
- [ ] trace schema has a version number;
- [ ] event schema is extensible;
- [ ] every event has a timestamp;
- [ ] every event has a run_id;
- [ ] every step has a step_id;
- [ ] JSON export is supported;
- [ ] OTLP-compatible export is supported;
- [ ] local SQLite store is supported;
- [ ] redaction hooks are supported;
- [ ] deterministic playback replay is supported;
- [ ] side-effectful tools are not re-executed by default;
- [ ] CLI has test coverage;
- [ ] examples run in CI.

### 15.3 Security and Privacy Acceptance

- [ ] local-first by default;
- [ ] traces are not uploaded by default;
- [ ] sensitive field redaction is supported;
- [ ] prompt/body capture can be disabled;
- [ ] metadata-only mode is supported;
- [ ] documentation warns that traces may contain prompts, tool results, PII, and secrets;
- [ ] `.agent-replayignore` is supported; *(Phase 2 — see §8.4)*
- [ ] sanitize command is available before export; *(Phase 2 — see §8.4)*
- [ ] side-effect replay requires explicit confirmation.

### 15.4 Research Grounding Acceptance

- [ ] README references ReAct;
- [ ] `docs/research.md` references AgentBench and WebArena;
- [ ] `docs/research.md` references Reflexion, ExpeL, and Voyager;
- [ ] `docs/research.md` references Generative Agents and MemGPT;
- [ ] `docs/research.md` references OpenTelemetry GenAI semantic conventions;
- [ ] `docs/research.md` references rr, CRIU, and snapshot-related systems work;
- [ ] every major ADR links back to at least one research or systems precedent.

### 15.5 Open-Source Release Acceptance

- [ ] MIT or Apache-2.0 license;
- [ ] `CONTRIBUTING.md`;
- [ ] `CODE_OF_CONDUCT.md`;
- [ ] `SECURITY.md`;
- [ ] issue templates;
- [ ] minimal examples;
- [ ] demo GIF;
- [ ] release v0.1 tag;
- [ ] PyPI package;
- [ ] documentation site or GitHub Pages;
- [ ] launch essay: “Tracing Is Not Enough: AI Agents Need Replay.”

---

## 16. Risks and Mitigations

### Risk 1: Existing Observability Platforms Add Similar Features

Mitigation:

- do not compete as a generic LLM observability dashboard;
- focus on replay, fork, and experience memory;
- remain local-first and framework-friendly;
- integrate with OpenTelemetry rather than replacing it.

### Risk 2: Replay Semantics Are Ambiguous

Mitigation:

- clearly distinguish deterministic replay from semantic replay;
- v0 only promises playback replay;
- v1 supports mocked replay;
- v2 supports forked replay;
- side-effectful tools are never automatically re-executed.

### Risk 3: Experience Memory Becomes a Garbage Pile

Mitigation:

- every experience must be linked to a source trace;
- every experience must include evidence;
- every experience must be evaluable;
- stale memory detection is required;
- manual approval is supported;
- namespace isolation is supported.

### Risk 4: The Initial Product Scope Becomes Too Large

Mitigation:

- v0 only includes Python SDK, SQLite, CLI, and examples;
- no hosted SaaS;
- no full UI;
- no distributed runtime;
- no OS-level replay.

---

## 17. Success Metrics

### v0.1 Success Metrics

- 500+ GitHub stars;
- 10+ external issues or pull requests;
- 3+ runnable examples;
- 5+ real trace feedback submissions from external users;
- meaningful discussion on Hacker News, Reddit, X, or relevant Discord communities;
- at least one agent framework maintainer expresses interest.

### v0.2 Success Metrics

- 1,000+ weekly Python SDK downloads;
- TypeScript SDK prototype completed;
- 5+ common failure detectors;
- 10+ real failure reports;
- at least one team uses the tool for internal agent debugging.

### v0.3 Success Metrics

- forked replay prototype completed;
- run diff supported;
- at least one user fixes a real agent bug with Agent Replay;
- at least one open-source agent project integrates Agent Replay.

### v1.0 Success Metrics

- Trace + Analyze + Replay + Fork form a coherent loop;
- Experience Memory demo shows measurable improvement in later runs;
- Python and TypeScript are both supported;
- OTLP export is supported;
- hosted or enterprise deployment path is clearly defined.

---

## 18. Conclusion

The core thesis behind Agent Replay is:

> As AI agents become more complex, developers will need not only observability, but replayability.

Traditional observability lets developers see the past. Agent Replay lets developers return to the past, change the branch, compare alternatives, and convert historical trajectories into future experience.

The right starting point is not a massive platform. The right starting point is a narrow but highly distinctive open-source developer tool:

```text
record → inspect → replay → fork → learn
```

The first version should focus on a Python SDK, local trace store, CLI, JSON/OTLP export, and high-quality failure examples. Once validated, the project can expand into failure analysis, checkpoint/fork, and experience memory.

The long-term vision is an:

> **Agent Experience Platform**

A platform that helps AI agents become observable, debuggable, replayable, and capable of learning from their own execution history.