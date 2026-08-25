"""``agent-replay`` command-line interface (Typer + rich).

Commands:
  list                       list recorded runs
  show   <run_id|latest>     render a run's timeline
  replay <run_id|latest>     playback the run (no external calls)
  export <run_id|latest>     export a run as JSON or OTLP/JSON
"""

from __future__ import annotations

import importlib
import json as _json

import typer
from rich.console import Console
from rich.table import Table
from rich.tree import Tree

from ..analysis import aggregate, analyze
from ..exporters import export_run, export_run_otlp
from ..redaction import DEFAULT_SECRET_PATTERNS, load_ignore_patterns, scrub
from ..replay import PlaybackReplay
from ..schema import (
    LLM_CALL,
    MEMORY_READ,
    MEMORY_WRITE,
    RETRIEVAL,
    TOOL_CALL,
    Run,
    Step,
)
from ..store import Store

app = typer.Typer(add_completion=False, help="Time-travel debugging for AI agents.")
console = Console()

_DB_OPTION = typer.Option(
    None, "--db", help="Path to the trace store (default: env / ~/.agent-replay/traces.db)."
)

_OUTPUT_OPTION = typer.Option(
    None, "--output", "-o", help="Write to file instead of stdout."
)

_TYPE_STYLE = {
    LLM_CALL: "cyan",
    TOOL_CALL: "yellow",
    RETRIEVAL: "magenta",
    MEMORY_READ: "blue",
    MEMORY_WRITE: "green",
}

_STATUS_STYLE = {"success": "green", "failed": "red", "running": "yellow"}


def _resolve_run(store: Store, run_ref: str) -> Run:
    run = store.latest_run() if run_ref == "latest" else store.get_run(run_ref)
    if run is None:
        msg = "No runs recorded yet." if run_ref == "latest" else f"Run not found: {run_ref}"
        console.print(f"[red]{msg}[/red]")
        raise typer.Exit(1)
    return run


def _compact(value: object, limit: int = 160) -> str:
    if value is None:
        return ""
    text = value if isinstance(value, str) else _json.dumps(value, default=str)
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _step_label(step: Step) -> str:
    style = _TYPE_STYLE.get(step.type, "white")
    header = f"[{style}]{step.type}[/{style}] [dim]{step.step_id}[/dim] {step.name or ''}".rstrip()
    lines = [header]
    if step.input is not None:
        lines.append(f"  [dim]input:[/dim]  {_compact(step.input)}")
    if step.output is not None:
        lines.append(f"  [dim]output:[/dim] {_compact(step.output)}")
    if step.usage:
        lines.append(f"  [dim]usage:[/dim]  {_compact(step.usage)}")
    if step.error:
        lines.append(f"  [red]error:  {_compact(step.error)}[/red]")
    return "\n".join(lines)


def _run_header(run: Run) -> str:
    status_style = _STATUS_STYLE.get(run.status, "white")
    parts = [
        f"[bold]{run.agent_name}[/bold]",
        f"[dim]{run.run_id}[/dim]",
        f"[{status_style}]{run.status}[/{status_style}]",
    ]
    if run.latency_ms is not None:
        parts.append(f"{run.latency_ms}ms")
    if run.cost_usd is not None:
        parts.append(f"${run.cost_usd:.4f}")
    header = "  ".join(parts)
    if run.task:
        header += f"\n[italic]{run.task}[/italic]"
    return header


def _timeline_tree(run: Run, steps: list[Step]) -> Tree:
    tree = Tree(_run_header(run))
    if not steps:
        tree.add("[dim]<no steps recorded>[/dim]")
    for step in steps:
        tree.add(_step_label(step))
    return tree


@app.command("list")
def list_runs(
    limit: int = typer.Option(50, "--limit", "-n", help="Max number of runs to show."),
    db: str | None = _DB_OPTION,
) -> None:
    """List recorded runs, most recent first."""
    store = Store(db)
    runs = store.list_runs(limit=limit)
    if not runs:
        console.print("[dim]No runs recorded yet.[/dim]")
        return
    table = Table(title="Agent Replay — runs")
    table.add_column("run_id", style="dim", no_wrap=True)
    table.add_column("agent")
    table.add_column("status")
    table.add_column("latency", justify="right")
    table.add_column("cost", justify="right")
    table.add_column("started_at", style="dim")
    table.add_column("task")
    for run in runs:
        status_style = _STATUS_STYLE.get(run.status, "white")
        table.add_row(
            run.run_id,
            run.agent_name,
            f"[{status_style}]{run.status}[/{status_style}]",
            f"{run.latency_ms}ms" if run.latency_ms is not None else "",
            f"${run.cost_usd:.4f}" if run.cost_usd is not None else "",
            run.started_at or "",
            _compact(run.task, 40),
        )
    console.print(table)


@app.command("show")
def show(
    run: str = typer.Argument("latest", help="Run id, or 'latest'."),
    db: str | None = _DB_OPTION,
) -> None:
    """Render a run's timeline."""
    store = Store(db)
    run_obj = _resolve_run(store, run)
    steps = store.get_steps(run_obj.run_id)
    console.print(_timeline_tree(run_obj, steps))


@app.command("replay")
def replay(
    run: str = typer.Argument("latest", help="Run id, or 'latest'."),
    db: str | None = _DB_OPTION,
) -> None:
    """Playback a recorded run step by step (no models/tools are called)."""
    store = Store(db)
    run_obj = _resolve_run(store, run)
    playback = PlaybackReplay(run_obj.run_id, store=store)
    console.print(_run_header(run_obj))
    console.print("[dim]playback replay — no external calls are made[/dim]\n")
    for i, step in enumerate(playback.steps(), start=1):
        console.print(f"[bold]{i:>2}.[/bold] {_step_label(step)}\n")
    console.print(f"[green]Replayed {len(playback)} steps.[/green]")


@app.command("export")
def export(
    run: str = typer.Argument("latest", help="Run id, or 'latest'."),
    format: str = typer.Option("json", "--format", "-f", help="json | otlp"),
    output: str | None = typer.Option(
        None, "--output", "-o", help="Write to file instead of stdout."
    ),
    db: str | None = _DB_OPTION,
) -> None:
    """Export a run as JSON or OTLP/JSON."""
    store = Store(db)
    run_obj = _resolve_run(store, run)
    steps = store.get_steps(run_obj.run_id)
    fmt = format.lower()
    if fmt == "json":
        payload = export_run(run_obj, steps)
    elif fmt == "otlp":
        payload = export_run_otlp(run_obj, steps)
    else:
        console.print(f"[red]Unknown format: {format} (expected 'json' or 'otlp')[/red]")
        raise typer.Exit(2)
    text = _json.dumps(payload, indent=2, default=str)
    if output:
        with open(output, "w", encoding="utf-8") as fh:
            fh.write(text)
        console.print(f"[green]Wrote {fmt} export to {output}[/green]")
    else:
        # Plain stdout (no rich markup) so the output is pipeable.
        print(text)


_SEVERITY_STYLE = {"high": "red", "medium": "yellow", "low": "cyan"}

_PLUGIN_OPTION = typer.Option(
    None, "--plugin", help="Import a module that registers custom detectors (repeatable)."
)


@app.command("analyze")
def analyze_cmd(
    run: str = typer.Argument("latest", help="Run id, or 'latest'."),
    format: str = typer.Option("text", "--format", "-f", help="text | json"),
    plugin: list[str] = _PLUGIN_OPTION,
    output: str | None = typer.Option(None, "--output", "-o", help="Write JSON to a file."),
    db: str | None = _DB_OPTION,
) -> None:
    """Analyze a run for likely failures and print an explainable report."""
    for mod in plugin or []:
        importlib.import_module(mod)
    store = Store(db)
    run_obj = _resolve_run(store, run)
    steps = store.get_steps(run_obj.run_id)
    report = analyze(run_obj, steps)

    if format.lower() == "json":
        text = _json.dumps(report.to_dict(), indent=2, default=str)
        if output:
            with open(output, "w", encoding="utf-8") as fh:
                fh.write(text)
            console.print(f"[green]Wrote analysis to {output}[/green]")
        else:
            print(text)
        return

    console.print(_run_header(run_obj))
    if report.success or not report.findings:
        console.print("\n[green]No failures detected.[/green]")
        return
    console.print("\n[bold]Likely root cause:[/bold]")
    for f in report.findings:
        style = _SEVERITY_STYLE.get(f.severity or "", "white")
        loc = f" [dim]({f.step_id})[/dim]" if f.step_id else ""
        console.print(
            f"  [{style}]•[/{style}] {f.message}{loc} "
            f"[dim]— {f.failure_type}, confidence {f.confidence:.2f}[/dim]"
        )
    if report.suggested_replay_step:
        console.print(
            f"\n[bold]Suggested replay point:[/bold] before {report.suggested_replay_step}"
        )
    sev_style = _SEVERITY_STYLE.get(report.severity, "white")
    console.print(
        f"[bold]Severity:[/bold] [{sev_style}]{report.severity}[/{sev_style}]   "
        f"[bold]Confidence:[/bold] {report.confidence:.2f}"
    )


@app.command("stats")
def stats_cmd(
    limit: int = typer.Option(200, "--limit", "-n", help="Max number of runs to analyze."),
    format: str = typer.Option("text", "--format", "-f", help="text | json"),
    db: str | None = _DB_OPTION,
) -> None:
    """Aggregate failure statistics across recorded runs."""
    store = Store(db)
    runs = store.list_runs(limit=limit)
    reports = [analyze(r, store.get_steps(r.run_id)) for r in runs]
    agg = aggregate(reports)

    if format.lower() == "json":
        print(_json.dumps(agg, indent=2, default=str))
        return

    console.print(
        f"[bold]{agg['total_runs']}[/bold] runs   "
        f"[green]{agg['successful_runs']} ok[/green]   "
        f"[red]{agg['failed_runs']} flagged[/red]   "
        f"success rate [bold]{agg['success_rate'] * 100:.0f}%[/bold]"
    )
    counts = agg["failure_type_counts"]
    if not counts:
        console.print("[dim]No failures detected across these runs.[/dim]")
        return
    table = Table(title="Failure types")
    table.add_column("failure_type")
    table.add_column("runs", justify="right")
    for ftype, count in counts.items():
        table.add_row(ftype, str(count))
    console.print(table)


@app.command("sanitize")
def sanitize_cmd(
    run: str = typer.Argument("latest", help="Run id, or 'latest'."),
    output: str | None = _OUTPUT_OPTION,
    db: str | None = _DB_OPTION,
) -> None:
    """Export a run as JSON with secret-bearing fields scrubbed (safe to share)."""
    store = Store(db)
    run_obj = _resolve_run(store, run)
    steps = store.get_steps(run_obj.run_id)
    patterns = tuple(dict.fromkeys([*DEFAULT_SECRET_PATTERNS, *load_ignore_patterns()]))
    for step in steps:
        step.input = scrub(step.input, patterns)
        step.output = scrub(step.output, patterns)
        step.state_before = scrub(step.state_before, patterns)
        step.state_after = scrub(step.state_after, patterns)
    payload = export_run(run_obj, steps)
    text = _json.dumps(payload, indent=2, default=str)
    if output:
        with open(output, "w", encoding="utf-8") as fh:
            fh.write(text)
        console.print(f"[green]Wrote sanitized export to {output}[/green]")
    else:
        print(text)


def main() -> None:
    """Console-script entry point."""
    app()


if __name__ == "__main__":
    main()
