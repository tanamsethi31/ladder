"""Ladder CLI — track every branch in your AI pair-programming sessions."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from ladder.core.git import auto_commit
from ladder.core.models import Effort, Ladder, Rung, Stage, Status
from ladder.core.parser import parse_ladder, write_ladder
from ladder.core.renderer import (
    render_next_suggestions,
    render_rung,
    render_status,
    render_tree,
    render_validation,
)

app = typer.Typer(
    name="ladder",
    help="Track every branch, stage, and alternative path in your AI pair-programming sessions.",
    no_args_is_help=True,
)
console = Console()

LADDER_DIR = Path(".ladder")
LADDER_FILE = LADDER_DIR / "ladder.md"


def _get_ladder_path() -> Path:
    """Resolve the ladder file path from current directory."""
    return LADDER_FILE.resolve()


def _load_ladder() -> tuple[Path, Ladder]:
    """Load the ladder file or exit with error."""
    path = _get_ladder_path()
    if not path.exists():
        console.print(
            Panel(
                Text("No ladder found. Run ", style="red")
                + Text("ladder init", style="bold yellow")
                + Text(" to create one.", style="red"),
                border_style="red",
            )
        )
        raise typer.Exit(1)
    return path, parse_ladder(path)


def _find_stage(ladder: Ladder, stage_name: str) -> Stage | None:
    """Find a stage by name (case-insensitive)."""
    for stage in ladder.stages:
        if stage.name.lower() == stage_name.lower():
            return stage
    return None


@app.command()
def init(
    project: str = typer.Option("My Project", "--project", "-p", help="Project name"),
) -> None:
    """Initialize a new ladder in the current directory."""
    path = _get_ladder_path()
    if path.exists():
        console.print(f"[yellow]Ladder already exists at {path}[/yellow]")
        raise typer.Exit(0)

    path.parent.mkdir(parents=True, exist_ok=True)

    ladder = Ladder(
        project=project,
        stages=[
            Stage(
                name="foundation",
                rungs=[
                    Rung(
                        id="R001",
                        title="Project scaffold & folder structure",
                        effort=Effort.SMALL,
                        context="Setting up the repo",
                        why="Everything builds on this",
                        created_at=datetime.now(),
                    ),
                ],
            ),
            Stage(
                name="core",
                rungs=[
                    Rung(
                        id="R002",
                        title="Your first real feature",
                        effort=Effort.MEDIUM,
                        context="What you are building right now",
                        why="The meat of the project",
                        created_at=datetime.now(),
                    ),
                ],
            ),
        ],
    )

    write_ladder(path, ladder)
    console.print(f"[green]✓[/green] Created ladder at [bold]{path}[/bold]")
    console.print()
    console.print("Next steps:")
    console.print("  1. Paste the system prompt into your AI assistant")
    console.print("  2. Start building — the AI will populate the ladder")
    console.print("  3. Run [bold]ladder status[/bold] anytime to see your progress")


@app.command()
def status(
    stage: str = typer.Option(None, "--stage", "-s", help="Filter by stage name"),
    effort: str = typer.Option(None, "--effort", "-e", help="Filter by effort (small/medium/large)"),
) -> None:
    """Show the full project ladder."""
    _, ladder = _load_ladder()
    render_status(ladder, console, filter_stage=stage, filter_effort=effort)


@app.command()
def show(rung_id: str = typer.Argument(..., help="Rung ID (e.g. R003)")) -> None:
    """Show detailed info for a specific rung."""
    _, ladder = _load_ladder()
    rung = ladder.get_rung(rung_id)
    if not rung:
        console.print(f"[red]Rung {rung_id} not found[/red]")
        raise typer.Exit(1)
    render_rung(rung, console)


@app.command()
def add(
    title: str = typer.Argument(..., help="Title of the new rung"),
    stage: str = typer.Option("core", "--stage", "-s", help="Stage to add to (creates if missing)"),
    effort: str = typer.Option("medium", "--effort", "-e", help="Effort: small, medium, large"),
    context: str = typer.Option("", "--context", "-c", help="What this rung is about"),
    why: str = typer.Option("", "--why", "-w", help="Why this matters"),
    blocked_by: str = typer.Option("", "--blocked-by", "-b", help="Comma-separated rung IDs that block this"),
    parent: str = typer.Option(None, "--parent", help="Parent rung ID"),
) -> None:
    """Add a new rung to the ladder."""
    path, ladder = _load_ladder()

    # Validate effort
    try:
        effort_enum = Effort(effort.lower())
    except ValueError:
        console.print(f"[red]Invalid effort: {effort}. Use small, medium, or large.[/red]")
        raise typer.Exit(1)

    # Generate next ID
    rung_id = ladder.next_rung_id()

    # Parse blockers
    blockers = [b.strip() for b in blocked_by.split(",") if b.strip()] if blocked_by else []

    # Validate blockers exist
    all_ids = ladder.all_rung_ids
    for blocker in blockers:
        if blocker not in all_ids:
            console.print(f"[yellow]Warning: blocker {blocker} does not exist yet[/yellow]")

    # Validate parent exists
    if parent and parent not in all_ids:
        console.print(f"[yellow]Warning: parent {parent} does not exist yet[/yellow]")

    new_rung = Rung(
        id=rung_id,
        title=title,
        effort=effort_enum,
        context=context,
        why=why,
        blocked_by=blockers,
        parent=parent,
        created_at=datetime.now(),
    )

    # Find or create stage
    target_stage = _find_stage(ladder, stage)
    if target_stage is None:
        target_stage = Stage(name=stage.lower())
        ladder.stages.append(target_stage)
        console.print(f"[dim]Created new stage: {stage.lower()}[/dim]")

    target_stage.rungs.append(new_rung)
    write_ladder(path, ladder)
    auto_commit(path, f"Add {rung_id}: {title}")

    console.print(f"[green]✓[/green] Added [bold]{rung_id}[/bold]: {title}")
    if blockers:
        console.print(f"   Blocked by: {', '.join(blockers)}")
    console.print(f"   Stage: {target_stage.name}  |  Effort: {effort_enum.value}")


@app.command()
def next() -> None:
    """Suggest the next rung(s) to work on."""
    _, ladder = _load_ladder()

    # Get unblocked rungs
    unblocked = ladder.get_unblocked_rungs()

    if not unblocked:
        console.print("[dim]No unblocked rungs available.[/dim]")
        # Show what's blocking
        blocked = [r for r in ladder.all_rungs if r.is_active and r.blocked_by]
        if blocked:
            console.print("\n[dim]These rungs are waiting on dependencies:[/dim]")
            for r in blocked:
                blockers = ", ".join(r.blocked_by)
                console.print(f"  {r.id} → blocked by {blockers}")
        return

    # Sort by: current stage first, then effort (small → medium → large), then by ID
    def sort_key(rung: Rung) -> tuple:
        # Find stage index
        for i, stage in enumerate(ladder.stages):
            if rung in stage.rungs:
                stage_idx = i
                break
        else:
            stage_idx = 999
        effort_order = {"small": 0, "medium": 1, "large": 2}
        return (stage_idx, effort_order.get(rung.effort.value, 1), rung.id)

    unblocked.sort(key=sort_key)
    render_next_suggestions(unblocked, console)


@app.command()
def validate() -> None:
    """Check ladder.md for errors and inconsistencies."""
    _, ladder = _load_ladder()
    errors: list[str] = []
    warnings: list[str] = []

    all_ids = ladder.all_rung_ids
    seen_ids: set[str] = set()

    for stage in ladder.stages:
        for rung in stage.rungs:
            # Duplicate IDs
            if rung.id in seen_ids:
                errors.append(f"Duplicate rung ID: {rung.id}")
            seen_ids.add(rung.id)

            # Broken dependencies
            for blocker in rung.blocked_by:
                if blocker not in all_ids:
                    errors.append(f"{rung.id}: blocker '{blocker}' does not exist")

            # Orphaned parent
            if rung.parent and rung.parent not in all_ids:
                errors.append(f"{rung.id}: parent '{rung.parent}' does not exist")

            # Self-blocking
            if rung.id in rung.blocked_by:
                errors.append(f"{rung.id}: cannot block itself")

            # Circular dependency (simple 1-hop check)
            for blocker in rung.blocked_by:
                blocker_rung = ladder.get_rung(blocker)
                if blocker_rung and rung.id in blocker_rung.blocked_by:
                    errors.append(f"Circular dependency: {rung.id} ↔ {blocker}")

            # Status vs checkbox mismatch
            if rung.status == Status.DONE and rung.options and not any(o.chosen for o in rung.options):
                warnings.append(f"{rung.id}: marked done but no option chosen")

            # Blocked but no blockers
            if rung.status == Status.BLOCKED and not rung.blocked_by:
                warnings.append(f"{rung.id}: status is blocked but no blockers listed")

            # Done but still has blockers
            if rung.is_done and rung.blocked_by:
                warnings.append(f"{rung.id}: is done but still lists blockers")

    render_validation(errors, warnings, console)

    if errors:
        raise typer.Exit(1)


@app.command()
def do(rung_id: str = typer.Argument(..., help="Rung ID to start working on")) -> None:
    """Mark a rung as in-progress."""
    path, ladder = _load_ladder()
    rung = ladder.get_rung(rung_id)
    if not rung:
        console.print(f"[red]Rung {rung_id} not found[/red]")
        raise typer.Exit(1)

    rung.status = Status.IN_PROGRESS
    write_ladder(path, ladder)
    auto_commit(path, f"Start work on {rung_id}: {rung.title}")
    console.print(f"[green]▶[/green] Now working on [bold]{rung_id}[/bold]: {rung.title}")


@app.command()
def complete(rung_id: str = typer.Argument(..., help="Rung ID to mark done")) -> None:
    """Mark a rung as completed."""
    path, ladder = _load_ladder()
    rung = ladder.get_rung(rung_id)
    if not rung:
        console.print(f"[red]Rung {rung_id} not found[/red]")
        raise typer.Exit(1)

    rung.status = Status.DONE
    rung.completed_at = datetime.now()
    write_ladder(path, ladder)
    auto_commit(path, f"Complete {rung_id}: {rung.title}")
    console.print(f"[green]✓[/green] Completed [bold]{rung_id}[/bold]: {rung.title}")


@app.command()
def abandon(
    rung_id: str = typer.Argument(..., help="Rung ID to abandon"),
    reason: str = typer.Option("", "--reason", "-r", help="Why this rung was abandoned"),
) -> None:
    """Mark a rung as abandoned."""
    path, ladder = _load_ladder()
    rung = ladder.get_rung(rung_id)
    if not rung:
        console.print(f"[red]Rung {rung_id} not found[/red]")
        raise typer.Exit(1)

    rung.status = Status.ABANDONED
    if reason:
        rung.note = f"Abandoned: {reason}"
    write_ladder(path, ladder)
    auto_commit(path, f"Abandon {rung_id}: {rung.title}")
    console.print(f"[dim]~[/dim] Abandoned [bold]{rung_id}[/bold]: {rung.title}")


@app.command()
def explore(rung_id: str = typer.Argument(..., help="Rung ID to explore")) -> None:
    """Mark a rung as exploring — you're investigating but not committed."""
    path, ladder = _load_ladder()
    rung = ladder.get_rung(rung_id)
    if not rung:
        console.print(f"[red]Rung {rung_id} not found[/red]")
        raise typer.Exit(1)

    rung.status = Status.EXPLORING
    write_ladder(path, ladder)
    auto_commit(path, f"Explore {rung_id}: {rung.title}")
    console.print(f"[cyan]?[/cyan] Exploring [bold]{rung_id}[/bold]: {rung.title}")


@app.command()
def reject(rung_id: str = typer.Argument(..., help="Rung ID to reject")) -> None:
    """Mark a rung as rejected — a decision was made against this path."""
    path, ladder = _load_ladder()
    rung = ladder.get_rung(rung_id)
    if not rung:
        console.print(f"[red]Rung {rung_id} not found[/red]")
        raise typer.Exit(1)

    rung.status = Status.REJECTED
    write_ladder(path, ladder)
    auto_commit(path, f"Reject {rung_id}: {rung.title}")
    console.print(f"[dim]~[/dim] Rejected [bold]{rung_id}[/bold]: {rung.title}")


@app.command()
def tree() -> None:
    """Show the ladder as a dependency tree."""
    _, ladder = _load_ladder()
    render_tree(ladder, console)


@app.command()
def prompt() -> None:
    """Print the system prompt to paste into your AI assistant."""
    prompt_path = Path(__file__).parent / "prompts" / "system.md"
    if prompt_path.exists():
        console.print(prompt_path.read_text(), markup=False, highlight=False)
    else:
        console.print("[red]Prompt file not found[/red]")


if __name__ == "__main__":
    app()
