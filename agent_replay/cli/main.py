"""``agent-replay`` command-line interface (Typer + rich).

Commands:
  list                       list recorded runs
  show   <run_id|latest>     render a run's timeline
  replay <run_id|latest>     playback the run (no external calls)
  export <run_id|latest>     export a run as JSON or OTLP/JSON
"""

from __future__ import annotations

import json as _json

import typer
from rich.console import Console
from rich.table import Table
from rich.tree import Tree

from ..exporters import export_run, export_run_otlp
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


def main() -> None:
    """Console-script entry point."""
    app()


if __name__ == "__main__":
    main()
