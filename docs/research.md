# Research and Systems Grounding

Agent Replay is a research-informed developer tool. This page collects the key papers and
systems that motivate its design. Each Architecture Decision Record in [`adr/`](adr/) links
back to at least one entry here.

## Reasoning + acting

- **ReAct: Synergizing Reasoning and Acting in Language Models** (Yao et al., 2022).
  Formalizes interleaving reasoning traces with task actions. This is the foundational
  abstraction for an agent *trajectory*: a trace is not a single prompt/response but a
  sequence of reasoning, action selection, tool calls, and observations. Motivates the
  `Step` model (`llm_call`, `tool_call`, `retrieval`, `memory_*`).

## Agent evaluation

- **AgentBench: Evaluating LLMs as Agents** (Liu et al., 2023). Multi-environment,
  multi-step agent evaluation; highlights long-horizon reasoning, decision-making, and
  instruction-following as major failure sources. Motivates a failure-first framing.
- **WebArena: A Realistic Web Environment for Building Autonomous Agents** (Zhou et al.,
  2023). Shows strong LLM agents still fail frequently on realistic web tasks, making
  reproducible traces and replay valuable.
- **SWE-bench** / **SWE-bench Verified** (Jimenez et al., 2023; OpenAI, 2024). Relevant to
  future coding-agent use cases where replay and failure diagnosis explain why an agent did
  or did not fix a real issue.

## Reflection and experience learning

- **Reflexion: Language Agents with Verbal Reinforcement Learning** (Shinn et al., 2023).
  Agents improve by reflecting on prior attempts. Grounds the Phase 4 direction:
  trace → reflection → reusable experience.
- **ExpeL: LLM Agents Are Experiential Learners** (Zhao et al., 2023). Directly aligned with
  Agent Replay's long-term goal of accumulating experience from past interactions.
- **Voyager: An Open-Ended Embodied Agent with Large Language Models** (Wang et al., 2023).
  Lifelong learning via environment feedback and a skill library.

## Long-term memory

- **Generative Agents: Interactive Simulacra of Human Behavior** (Park et al., 2023).
  Memory streams, reflection, and planning for continuity across interactions.
- **MemGPT: Towards LLMs as Operating Systems** (Packer et al., 2023). Treats the context
  window as limited memory with virtual context management across tiers. Motivates
  evaluating memory by whether it improves *future* behavior, not just storing text.
- Recent surveys on LLM-agent memory mechanisms position memory as a critical capability for
  long-running agent behavior.

## Telemetry standards

- **OpenTelemetry GenAI semantic conventions.** OTel is moving toward standardized spans and
  attributes for GenAI calls, tools, and agent frameworks (`gen_ai.*`). Agent Replay does
  **not** replace OpenTelemetry; it builds an agent-specific debugging primitive on top of
  these concepts and can export OTLP/JSON. See [`../agent_replay/exporters/otlp.py`](../agent_replay/exporters/otlp.py).

## Record/replay and checkpointing systems

- **rr** (Mozilla). Record-once, replay-deterministically debugging with reverse execution;
  the inspiration for "return to the failure point."
- **CRIU** (Checkpoint/Restore In Userspace). Linux process/container checkpoint and restore.
- **Firecracker** and microVM snapshot/restore work. Snapshot/restore as a primitive for
  short-lived compute.

Agent Replay borrows the *spirit* of these systems but deliberately does **not** attempt
OS-level deterministic replay. Instead it implements **semantic replay for AI agents**:
record semantic execution steps, freeze LLM/tool/retrieval/memory inputs and outputs, and
(in later phases) modify configuration or mock outputs from a selected step onward. See
[`adr/002-semantic-replay.md`](adr/002-semantic-replay.md).
