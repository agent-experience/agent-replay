---
title: "Langfuse vs LangSmith vs Agent Replay: AI Agent Observability Compared"
description: Feature-by-feature comparison of Langfuse, LangSmith, and Agent Replay for AI agent debugging and observability — pricing, self-hosting, failure detection, and replay capabilities.
head:
  - - meta
    - property: og:title
      content: "Langfuse vs LangSmith vs Agent Replay: AI Agent Observability Compared"
  - - meta
    - property: og:description
      content: Feature-by-feature comparison of Langfuse, LangSmith, and Agent Replay for AI agent debugging and observability — pricing, self-hosting, failure detection, and replay capabilities.
  - - meta
    - property: og:type
      content: article
---

# Langfuse vs LangSmith vs Agent Replay

Three tools that record what AI agents do. Different answers to what happens next.

**Langfuse** and **LangSmith** are observability platforms — they collect traces and help you inspect them. **Agent Replay** is a debugging tool — it records traces locally, replays them without API calls, and runs deterministic failure detectors to tell you *why* your agent made a wrong decision.

This page compares all three on the dimensions that matter when choosing a tool: what you can see, what you can do with it, where your data lives, and what it costs.

## Feature Comparison

| | Langfuse | LangSmith | Agent Replay |
|---|---|---|---|
| **Primary focus** | Observability + evals | Observability + evals + deployment | Debugging + failure detection |
| **Trace collection** | Yes | Yes | Yes |
| **Failure detection** | Manual inspection | Manual inspection + Engine (auto root cause) | [10 deterministic detectors](/failure-patterns) — no LLM calls |
| **Replay** | Re-run with live models | Re-run with live models | Deterministic replay, zero API calls |
| **Prompt management** | Built-in versioning + playground | Built-in versioning | Not included |
| **Evaluation** | LLM-as-judge, code evals, human feedback | LLM-as-judge, side-by-side, annotations | Deterministic detectors, custom plugins |
| **Agent deployment** | No | Yes (serverless + Fleet) | No |
| **Data location** | Their cloud or self-hosted | Their cloud (US/EU/APAC) or self-hosted | Your machine only (SQLite) |
| **Self-hosted** | Yes (open-source, Docker/K8s) | Enterprise plan only | Always local — nothing to host |
| **License** | MIT | Proprietary (cloud), source-available (some) | Apache 2.0 |
| **Framework lock-in** | None (OTel native, 100+ integrations) | None (framework agnostic) | None (JSON trace format) |
| **Languages** | Python, JS/TS, OpenTelemetry | Python, JS/TS | Python, TypeScript |
| **Free tier** | 50k units/mo, 2 users | 5k traces/mo, 1 user | Unlimited — fully free |
| **Paid plans** | From $29/mo | From $39/seat/mo | None |
| **GitHub stars** | ~29,000 | ~6,000 (LangChain org) | Early stage |

## When to Use Each Tool

### Choose Langfuse when

You need a **production observability platform** with prompt management. Langfuse is the strongest choice when your team needs collaborative debugging across multiple people, prompt versioning with a built-in playground, and a self-hosted option on your own infrastructure. The MIT license means no licensing surprises.

**Best for:** Teams running LLM applications in production who need shared dashboards, alerts (Slack/webhook), and prompt iteration workflows.

### Choose LangSmith when

You need **end-to-end agent lifecycle management** — from development through deployment. LangSmith is the only option here that includes agent deployment infrastructure (serverless hosting, sandboxes, Fleet for no-code agents). The Engine feature provides automated root cause analysis for production failures, similar in spirit to Agent Replay's detectors but running in the cloud with LLM assistance.

**Best for:** Teams deeply invested in the agent deployment pipeline who want observability, evaluation, and hosting in one platform.

### Choose Agent Replay when

You need to **understand why an agent made a specific wrong decision** — and you need your data to stay on your machine. Agent Replay is purpose-built for the debugging workflow: record a trace, replay the exact execution without calling any APIs, and get deterministic failure analysis in milliseconds.

**Best for:** Developers debugging agent failures during development, teams with strict data privacy requirements, and anyone who wants failure detection without ongoing costs.

## Detailed Comparison

### Failure Detection

This is where the tools diverge most.

**Langfuse** provides trace visualization — you can inspect every step of an agent's execution — but identifying *why* something went wrong is manual work. You look at the traces and figure it out yourself.

**LangSmith Engine** automates failure diagnosis using LLM calls to analyze traces. It clusters similar failures and proposes fixes. This is powerful but means every analysis consumes tokens and requires cloud access.

**Agent Replay** takes a different approach: [ten deterministic detectors](/failure-patterns) that identify specific failure patterns — hallucinated arguments, ignored tool results, loops, final answer conflicts, and more. No LLM calls means results in milliseconds, zero cost per analysis, and no data leaving your machine. The tradeoff: deterministic rules catch known patterns, not novel failure modes.

### Replay Capability

**Langfuse and LangSmith** let you re-run executions, but this means calling live models and tools again. Every replay costs money, takes time, and may produce different results due to model non-determinism.

**Agent Replay** records complete [traces](/guide/trace-schema) (inputs, outputs, state snapshots) and replays them deterministically. You inspect the exact same execution as many times as needed, at zero cost. When a bug appears at step 9 of a 10-step agent run, you jump directly to that step instead of re-running steps 1 through 8.

### Data Privacy

**Langfuse** cloud stores traces on their infrastructure. Self-hosted Langfuse keeps data on your servers but requires running the platform (Docker/Kubernetes + ClickHouse).

**LangSmith** cloud stores traces in their data centers (US, EU, or APAC region). Self-hosted deployment is available on the Enterprise plan.

**Agent Replay** stores traces in a local SQLite database. No network calls, no accounts, no cloud. Built-in [privacy features](/guide/privacy) include metadata-only mode, `.agent-replayignore`, redaction hooks, and a sanitize command for sharing traces safely.

### Pricing

**Langfuse** free tier: 50,000 units/month, 2 users, 30-day retention. Paid plans start at $29/month (Core) and scale to $2,499/month (Enterprise). Self-hosting is free under the MIT license.

**LangSmith** free tier: 5,000 traces/month, 1 user. Plus plan is $39/seat/month. Enterprise pricing is custom. Additional usage is metered in LCUs at $1.50 each.

**Agent Replay** is free. Apache 2.0 license. No tiers, no usage limits, no accounts. The entire tool runs locally.

### Integrations

**Langfuse** has the broadest integration ecosystem: 100+ framework integrations, native OpenTelemetry support, and SDKs for Python and JavaScript. If your stack uses OpenAI, LangChain, LlamaIndex, or any OTel-compatible framework, Langfuse likely has a one-line integration.

**LangSmith** is framework agnostic despite being built by the LangChain team. Supports MCP and A2A protocols. Python and JS/TS SDKs.

**Agent Replay** provides Python and [TypeScript](/api/typescript-sdk) SDKs plus a language-neutral [JSON trace format](/guide/trace-schema). Any language that can produce JSON can feed traces into Agent Replay. Fewer pre-built integrations, but the trace format is simple enough that adding a new one is a few lines of code.

## Can You Use Them Together?

Yes. These tools solve different problems and can complement each other:

- Use **Langfuse or LangSmith** for production monitoring, dashboards, and team-wide observability
- Use **Agent Replay** during development for deep debugging, deterministic replay, and failure pattern detection

Agent Replay's [JSON trace format](/guide/trace-schema) is designed to be portable. Export traces from your observability platform, import them into Agent Replay for offline analysis, and keep sensitive traces local.

## Summary

| Decision factor | Winner |
|---|---|
| Production observability | Langfuse or LangSmith |
| Agent deployment | LangSmith |
| Debugging root cause | Agent Replay |
| Data stays on your machine | Agent Replay |
| Free, forever | Agent Replay |
| Team collaboration | Langfuse |
| Prompt management | Langfuse or LangSmith |
| Integration ecosystem | Langfuse |
| Enterprise compliance | LangSmith or Langfuse |

No single tool does everything. Pick based on your primary constraint: **privacy and debugging depth** → Agent Replay. **Production observability for a team** → Langfuse. **Full lifecycle platform** → LangSmith.

## Get Started

```bash
pip install agent-replay
```

Record your first trace and run failure analysis in under 5 minutes — see the [Getting Started guide](/guide/getting-started).
