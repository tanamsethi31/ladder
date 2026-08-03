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
    LADDER_THEME,
    render_html,
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
console = Console(theme=LADDER_THEME)


@app.callback()
def _main(
    no_color: bool = typer.Option(
        False,
        "--no-color",
        help="Force plain output with no ANSI codes, regardless of terminal detection "
        "or FORCE_COLOR. Use this when relaying output somewhere that can't render "
        "ANSI (e.g. pasting into a chat response) to avoid garbled escape sequences.",
    ),
) -> None:
    if no_color:
        global console
        console = Console(theme=LADDER_THEME, no_color=True, force_terminal=False)


LADDER_DIR = Path(".ladder")
LADDER_FILE = LADDER_DIR / "ladder.md"
DEFAULT_EXPORT_FILE = LADDER_DIR / "ladder.html"


def _get_ladder_path() -> Path:
    """Resolve the ladder file path from current directory."""
    return LADDER_FILE.resolve()


def _load_ladder() -> tuple[Path, Ladder]:
    """Load the ladder file or exit with error."""
    path = _get_ladder_path()
    if not path.exists():
        console.print(
            Panel(
                Text("No ladder found. Run ", style="danger")
                + Text("ladder init", style="warning.bold")
                + Text(" to create one.", style="danger"),
                border_style="danger",
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


EFFORT_ORDER = {"small": 0, "medium": 1, "large": 2}
EFFORT_POINTS = {"small": 1, "medium": 2, "large": 3}


def _priority_sort_key(ladder: Ladder, rung: Rung) -> tuple[int, int, str]:
    """Sort by: current stage first, then effort (small → medium → large), then by ID."""
    for i, stage in enumerate(ladder.stages):
        if rung in stage.rungs:
            stage_idx = i
            break
    else:
        stage_idx = 999
    return (stage_idx, EFFORT_ORDER.get(rung.effort.value, 1), rung.id)


@app.command()
def init(
    project: str = typer.Option("My Project", "--project", "-p", help="Project name"),
) -> None:
    """Initialize a new ladder in the current directory."""
    path = _get_ladder_path()
    if path.exists():
        console.print(f"[warning]Ladder already exists at {path}[/warning]")
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
    console.print(f"[success]✓[/success] Created ladder at [bold]{path}[/bold]")
    console.print()
    console.print("Next steps:")
    console.print("  1. Paste the system prompt into your AI assistant")
    console.print("  2. Start building — the AI will populate the ladder")
    console.print("  3. Run [bold]ladder status[/bold] anytime to see your progress")


@app.command()
def status(
    stage: str = typer.Option(None, "--stage", "-s", help="Filter by stage name"),
    effort: str = typer.Option(
        None, "--effort", "-e", help="Filter by effort (small/medium/large)"
    ),
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
        console.print(f"[danger]Rung {rung_id} not found[/danger]")
        raise typer.Exit(1)
    render_rung(rung, console)


@app.command()
def add(
    title: str = typer.Argument(..., help="Title of the new rung"),
    stage: str = typer.Option("core", "--stage", "-s", help="Stage to add to (creates if missing)"),
    effort: str = typer.Option("medium", "--effort", "-e", help="Effort: small, medium, large"),
    context: str = typer.Option("", "--context", "-c", help="What this rung is about"),
    why: str = typer.Option("", "--why", "-w", help="Why this matters"),
    blocked_by: str = typer.Option(
        "", "--blocked-by", "-b", help="Comma-separated rung IDs that block this"
    ),
    parent: str = typer.Option(None, "--parent", help="Parent rung ID"),
) -> None:
    """Add a new rung to the ladder."""
    path, ladder = _load_ladder()

    # Validate effort
    try:
        effort_enum = Effort(effort.lower())
    except ValueError:
        console.print(f"[danger]Invalid effort: {effort}. Use small, medium, or large.[/danger]")
        raise typer.Exit(1) from None

    # Generate next ID
    rung_id = ladder.next_rung_id()

    # Parse blockers
    blockers = [b.strip() for b in blocked_by.split(",") if b.strip()] if blocked_by else []

    # Validate blockers exist
    all_ids = ladder.all_rung_ids
    for blocker in blockers:
        if blocker not in all_ids:
            console.print(f"[warning]Warning: blocker {blocker} does not exist yet[/warning]")

    # Validate parent exists
    if parent and parent not in all_ids:
        console.print(f"[warning]Warning: parent {parent} does not exist yet[/warning]")

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

    console.print(f"[success]✓[/success] Added [bold]{rung_id}[/bold]: {title}")
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

    unblocked.sort(key=lambda r: _priority_sort_key(ladder, r))
    render_next_suggestions(unblocked, console)

    # Stage progression nudge: flag stages ≥50% done with active rungs still remaining
    for stage in ladder.stages:
        total = len(stage.rungs)
        done = sum(1 for r in stage.rungs if r.is_done)
        if total >= 2 and done > 0 and stage.active_rungs and done / total >= 0.5:
            console.print(
                f"[dim]💡 `{stage.name}` is {done}/{total} done — "
                "consider finishing it before moving on.[/dim]"
            )


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
            if (
                rung.status == Status.DONE
                and rung.options
                and not any(o.chosen for o in rung.options)
            ):
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
        console.print(f"[danger]Rung {rung_id} not found[/danger]")
        raise typer.Exit(1)

    rung.status = Status.IN_PROGRESS
    write_ladder(path, ladder)
    auto_commit(path, f"Start work on {rung_id}: {rung.title}")
    console.print(f"[success]▶[/success] Now working on [bold]{rung_id}[/bold]: {rung.title}")


@app.command()
def complete(rung_id: str = typer.Argument(..., help="Rung ID to mark done")) -> None:
    """Mark a rung as completed."""
    path, ladder = _load_ladder()
    rung = ladder.get_rung(rung_id)
    if not rung:
        console.print(f"[danger]Rung {rung_id} not found[/danger]")
        raise typer.Exit(1)

    rung.status = Status.DONE
    rung.completed_at = datetime.now()
    write_ladder(path, ladder)
    auto_commit(path, f"Complete {rung_id}: {rung.title}")
    console.print(f"[success]✓[/success] Completed [bold]{rung_id}[/bold]: {rung.title}")


@app.command()
def note(
    rung_id: str = typer.Argument(..., help="Rung ID"),
    text: str = typer.Argument(..., help="Note text"),
) -> None:
    """Attach a note to a rung."""
    path, ladder = _load_ladder()
    rung = ladder.get_rung(rung_id)
    if not rung:
        console.print(f"[danger]Rung {rung_id} not found[/danger]")
        raise typer.Exit(1)

    rung.note = text
    write_ladder(path, ladder)
    auto_commit(path, f"Note on {rung_id}")
    console.print(f"[success]✓[/success] Noted on [bold]{rung_id}[/bold]: {text}")


@app.command()
def sprint(
    budget: int = typer.Option(
        5, "--budget", "-b", help="Effort points to fill (small=1, medium=2, large=3)"
    ),
) -> None:
    """Pick unblocked rungs that fit within an effort budget."""
    _, ladder = _load_ladder()
    unblocked = ladder.get_unblocked_rungs()
    unblocked.sort(key=lambda r: _priority_sort_key(ladder, r))

    picked: list[Rung] = []
    total = 0
    for rung in unblocked:
        cost = EFFORT_POINTS.get(rung.effort.value, 2)
        if total + cost <= budget:
            picked.append(rung)
            total += cost

    render_next_suggestions(
        picked, console, limit=None, header=f"🏁 Sprint plan — {total}/{budget} pts"
    )


@app.command()
def abandon(
    rung_id: str = typer.Argument(..., help="Rung ID to abandon"),
    reason: str = typer.Option("", "--reason", "-r", help="Why this rung was abandoned"),
) -> None:
    """Mark a rung as abandoned."""
    path, ladder = _load_ladder()
    rung = ladder.get_rung(rung_id)
    if not rung:
        console.print(f"[danger]Rung {rung_id} not found[/danger]")
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
        console.print(f"[danger]Rung {rung_id} not found[/danger]")
        raise typer.Exit(1)

    rung.status = Status.EXPLORING
    write_ladder(path, ladder)
    auto_commit(path, f"Explore {rung_id}: {rung.title}")
    console.print(f"[info]?[/info] Exploring [bold]{rung_id}[/bold]: {rung.title}")


@app.command()
def reject(rung_id: str = typer.Argument(..., help="Rung ID to reject")) -> None:
    """Mark a rung as rejected — a decision was made against this path."""
    path, ladder = _load_ladder()
    rung = ladder.get_rung(rung_id)
    if not rung:
        console.print(f"[danger]Rung {rung_id} not found[/danger]")
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
def export(
    out: str = typer.Option(str(DEFAULT_EXPORT_FILE), "--out", "-o", help="Output HTML file path"),
) -> None:
    """Export the ladder as a static HTML file."""
    _, ladder = _load_ladder()
    out_path = Path(out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(render_html(ladder), encoding="utf-8")
    console.print(f"[success]✓[/success] Exported ladder to [bold]{out_path}[/bold]")


@app.command()
def prompt() -> None:
    """Print the system prompt to paste into your AI assistant."""
    prompt_path = Path(__file__).parent / "prompts" / "system.md"
    if prompt_path.exists():
        console.print(prompt_path.read_text(), markup=False, highlight=False)
    else:
        console.print("[danger]Prompt file not found[/danger]")


if __name__ == "__main__":
    app()
