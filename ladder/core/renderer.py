"""Rich terminal rendering for the ladder."""

from __future__ import annotations

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.tree import Tree

from ladder.core.models import Ladder, Rung, Stage, Status


def _effort_style(effort: str) -> str:
    return {
        "small": "green",
        "medium": "yellow",
        "large": "red",
    }.get(effort, "white")


def _status_emoji(status: Status) -> str:
    return {
        Status.DONE: "✓",
        Status.IN_PROGRESS: "▶",
        Status.EXPLORING: "?",
        Status.OPEN: "○",
        Status.BLOCKED: "✕",
        Status.ABANDONED: "~",
        Status.REJECTED: "~",
    }.get(status, "○")


def _stage_dot(stage: Stage) -> str:
    if stage.is_complete:
        return "●"
    if stage.has_progress:
        return "◐"
    if stage.any_done:
        return "◑"
    return "○"


def _rung_style(rung: Rung) -> str:
    if rung.status == Status.BLOCKED:
        return "dim red"
    if rung.status == Status.ABANDONED or rung.status == Status.REJECTED:
        return "dim strike"
    if rung.is_done:
        return "dim strike"
    if rung.status == Status.IN_PROGRESS:
        return "bold yellow"
    if rung.status == Status.EXPLORING:
        return "italic cyan"
    return "white"


def render_status(ladder: Ladder, console: Console | None = None, filter_stage: str | None = None, filter_effort: str | None = None) -> None:
    """Render the full ladder status to the terminal."""
    if console is None:
        console = Console()

    # Header
    header = Text()
    header.append("🪜 ", style="bold")
    header.append(f"{ladder.project}", style="bold white")
    header.append(f"  v{ladder.version}  ", style="dim")
    header.append(
        f"{ladder.completed_count} done · "
        f"{ladder.in_progress_count} active · "
        f"{ladder.exploring_count} exploring · "
        f"{ladder.open_count} open · "
        f"{ladder.blocked_count} blocked",
        style="dim",
    )
    console.print(header)
    console.print()

    # Stats bar
    stats = Table.grid(padding=(0, 4))
    stats.add_column(justify="center")
    stats.add_column(justify="center")
    stats.add_column(justify="center")
    stats.add_column(justify="center")
    stats.add_column(justify="center")
    stats.add_row(
        Text(str(ladder.completed_count), style="bold green", justify="center"),
        Text(str(ladder.in_progress_count), style="bold yellow", justify="center"),
        Text(str(ladder.exploring_count), style="bold cyan", justify="center"),
        Text(str(ladder.open_count), style="bold white", justify="center"),
        Text(str(ladder.blocked_count), style="bold red", justify="center"),
    )
    stats.add_row(
        Text("done", style="dim", justify="center"),
        Text("active", style="dim", justify="center"),
        Text("exploring", style="dim", justify="center"),
        Text("open", style="dim", justify="center"),
        Text("blocked", style="dim", justify="center"),
    )
    console.print(Panel(stats, box=box.ROUNDED, border_style="dim"))
    console.print()

    # Stages
    for stage in ladder.stages:
        if filter_stage and stage.name != filter_stage.lower():
            continue

        dot = _stage_dot(stage)
        dot_style = {
            "●": "green",
            "◐": "yellow",
            "◑": "yellow",
            "○": "dim",
        }.get(dot, "dim")

        console.print(Text(f"{dot} {stage.name}", style=f"bold {dot_style}"))

        for rung in stage.rungs:
            if filter_effort and rung.effort.value != filter_effort.lower():
                continue

            emoji = _status_emoji(rung.status)
            effort_color = _effort_style(rung.effort.value)
            rung_style = _rung_style(rung)

            line = Text()
            line.append(f"  {emoji} ", style="dim")
            line.append(f"{rung.id}  ", style="dim")
            line.append(rung.title, style=rung_style)
            line.append(f"  → {rung.effort.value}", style=effort_color)

            if rung.blocked_by:
                blockers = ", ".join(rung.blocked_by)
                line.append(f"  [blocked by {blockers}]", style="red dim")

            console.print(line)

            if rung.why and not rung.is_done:
                console.print(Text(f"     {rung.why}", style="dim italic"))

        console.print()


def render_tree(ladder: Ladder, console: Console | None = None) -> None:
    """Render the ladder as an ASCII dependency tree."""
    if console is None:
        console = Console()

    root = Tree(f"[bold]{ladder.project}[/bold]")

    for stage in ladder.stages:
        stage_node = root.add(f"[bold]{stage.name}[/bold]")
        for rung in stage.rungs:
            emoji = _status_emoji(rung.status)
            effort_color = _effort_style(rung.effort.value)
            style = _rung_style(rung)
            label = f"{emoji} [bold]{rung.id}[/bold] [{style}]{rung.title}[/{style}] → [{effort_color}]{rung.effort.value}[/{effort_color}]"
            rung_node = stage_node.add(label)

            if rung.blocked_by:
                blockers = ", ".join(rung.blocked_by)
                rung_node.add(f"[red]← blocked by {blockers}[/red]")
            if rung.parent:
                rung_node.add(f"[dim]← parent: {rung.parent}[/dim]")
            if rung.why:
                rung_node.add(f"[dim italic]↳ {rung.why}[/dim italic]")

    console.print(root)


def render_rung(rung: Rung, console: Console | None = None) -> None:
    """Render a single rung in detail."""
    if console is None:
        console = Console()

    effort_color = _effort_style(rung.effort.value)
    status_emoji = _status_emoji(rung.status)

    title = Text()
    title.append(f"{status_emoji} ", style="bold")
    title.append(f"{rung.id}", style="bold")
    title.append(f"  {rung.title}", style="bold white")

    console.print(Panel(title, border_style=effort_color))

    info = Table(show_header=False, box=None, padding=(0, 2))
    info.add_column(style="dim", justify="right")
    info.add_column()

    info.add_row("Effort:", Text(rung.effort.value, style=effort_color))
    info.add_row("Status:", rung.status.value.replace("_", " "))
    if rung.context:
        info.add_row("Context:", rung.context)
    if rung.why:
        info.add_row("Why:", rung.why)
    if rung.parent:
        info.add_row("Parent:", rung.parent)
    if rung.blocked_by:
        info.add_row("Blocked by:", ", ".join(rung.blocked_by))
    if rung.note:
        info.add_row("Note:", rung.note)
    if rung.created_at:
        info.add_row("Created:", rung.created_at.strftime("%Y-%m-%d %H:%M"))
    if rung.completed_at:
        info.add_row("Completed:", rung.completed_at.strftime("%Y-%m-%d %H:%M"))

    console.print(info)

    if rung.options:
        console.print()
        console.print(Text("Options:", style="bold dim"))
        for opt in rung.options:
            check = "[x]" if opt.chosen else "[ ]"
            style = "green" if opt.chosen else "white"
            console.print(f"  {check} {opt.text}", style=style)


def render_next_suggestions(rungs: list[Rung], console: Console | None = None) -> None:
    """Render suggested next rungs."""
    if console is None:
        console = Console()

    if not rungs:
        console.print("[dim]No unblocked rungs available.[/dim]")
        console.print("[dim]All active rungs are blocked or complete.[/dim]")
        return

    console.print(Text("🎯 Suggested next rungs", style="bold yellow"))
    console.print()

    for i, rung in enumerate(rungs[:5], 1):
        effort_color = _effort_style(rung.effort.value)
        stage_name = ""
        # Find stage name
        # We don't have ladder here, so we can't look it up easily
        # Just show the rung
        line = Text()
        line.append(f"{i}. ", style="bold")
        line.append(f"{rung.id}  ", style="dim")
        line.append(rung.title, style="bold white")
        line.append(f"  → {rung.effort.value}", style=effort_color)
        console.print(line)
        if rung.why:
            console.print(Text(f"   {rung.why}", style="dim italic"))
        if rung.blocked_by:
            console.print(Text(f"   [will unblock: {', '.join(rung.blocked_by)}]", style="dim"))
        console.print()


def render_validation(errors: list[str], warnings: list[str], console: Console | None = None) -> None:
    """Render validation results."""
    if console is None:
        console = Console()

    if not errors and not warnings:
        console.print("[green]✓[/green] Ladder is valid. No issues found.")
        return

    if errors:
        console.print(Text(f"✕ {len(errors)} error(s) found:", style="bold red"))
        for err in errors:
            console.print(f"  [red]•[/red] {err}")
        console.print()

    if warnings:
        console.print(Text(f"⚠ {len(warnings)} warning(s) found:", style="bold yellow"))
        for warn in warnings:
            console.print(f"  [yellow]•[/yellow] {warn}")
