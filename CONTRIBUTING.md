# Contributing to Agent Replay

Thanks for your interest! Agent Replay is an open-source, local-first debugging tool for AI
agents. Contributions of code, examples, failure traces, and docs are all welcome.

## Development setup

```bash
git clone https://github.com/agent-experience/agent-replay.git
cd agent-replay
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
```

## Before you open a PR

```bash
ruff check .        # lint
pytest              # full test suite (includes running the examples)
```

- Every new detector, exporter, or CLI command should have unit tests.
- New event/step behavior should keep the trace schema backward-compatible (see
  [`docs/adr/001-agent-trace-schema.md`](docs/adr/001-agent-trace-schema.md)); bump
  `SCHEMA_VERSION` for breaking changes.
- Examples must run without API keys (use mock LLMs/tools) so they pass in CI.
- Keep the core package dependency-light (`typer`, `rich`); put heavier integrations behind
  optional extras.

## Scope

Please keep PRs aligned with the current phase (see the roadmap in
[`docs/whitepaper.md`](docs/whitepaper.md)). Phase 1 (trace + playback replay) and Phase 2
(failure analysis + eval) have shipped; checkpoint/fork and experience memory come later.

## Reporting bugs with a trace

The most useful bug reports include a **sanitized** trace. Use the "Bug report with trace"
issue template, and remove any prompts, tool results, PII, or secrets first — see
[`SECURITY.md`](SECURITY.md).

## Code of Conduct

By participating you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md).
