"""Rich terminal rendering for the ladder."""

from __future__ import annotations

from html import escape

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


def render_status(
    ladder: Ladder,
    console: Console | None = None,
    filter_stage: str | None = None,
    filter_effort: str | None = None,
) -> None:
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

        visible_rungs = [
            r for r in stage.rungs if not filter_effort or r.effort.value == filter_effort.lower()
        ]
        if not visible_rungs:
            continue

        dot = _stage_dot(stage)
        dot_style = {
            "●": "green",
            "◐": "yellow",
            "◑": "yellow",
            "○": "dim",
        }.get(dot, "dim")

        console.print(Text(f"{dot} {stage.name}", style=f"bold {dot_style}"))
        console.print()
        console.print(_render_rung_table(visible_rungs))
        console.print()


def _render_rung_table(rungs: list[Rung]) -> Table:
    """A table of rungs, one row each, with alternative options nested inside the row."""
    table = Table(box=box.SIMPLE_HEAD, show_edge=False, pad_edge=False, expand=False)
    table.add_column("", width=1)
    table.add_column("Rung", ratio=1)
    table.add_column("Effort", justify="right")

    for rung in rungs:
        emoji = _status_emoji(rung.status)
        effort_color = _effort_style(rung.effort.value)
        rung_style = _rung_style(rung)

        body = Text()
        body.append(f"{rung.id}  ", style="dim")
        body.append(rung.title, style=rung_style)
        if rung.blocked_by:
            body.append(f"  [blocked by {', '.join(rung.blocked_by)}]", style="red dim")

        if rung.why and not rung.is_done:
            body.append("\n   ")
            body.append(rung.why, style="dim italic")

        for opt in rung.options:
            body.append("\n   ")
            if opt.chosen:
                body.append("✓ ", style="bold green")
                body.append(opt.text, style="green")
            else:
                body.append("○ ", style="dim")
                body.append(opt.text, style="dim")

        table.add_row(
            Text(emoji, style=rung_style),
            body,
            Text(rung.effort.value, style=effort_color),
        )

    return table


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
            label = (
                f"{emoji} [bold]{rung.id}[/bold] [{style}]{rung.title}[/{style}] → "
                f"[{effort_color}]{rung.effort.value}[/{effort_color}]"
            )
            rung_node = stage_node.add(label)

            if rung.blocked_by:
                blockers = ", ".join(rung.blocked_by)
                rung_node.add(f"[red]← blocked by {blockers}[/red]")
            if rung.parent:
                rung_node.add(f"[dim]← parent: {rung.parent}[/dim]")
            if rung.why:
                rung_node.add(f"[dim italic]↳ {rung.why}[/dim italic]")
            for opt in rung.options:
                mark = "[bold green]✓[/bold green]" if opt.chosen else "[dim]○[/dim]"
                text_style = "green" if opt.chosen else "dim"
                rung_node.add(f"{mark} [{text_style}]{opt.text}[/{text_style}]")

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


def render_next_suggestions(
    rungs: list[Rung],
    console: Console | None = None,
    limit: int | None = 5,
    header: str = "🎯 Suggested next rungs",
) -> None:
    """Render suggested next rungs."""
    if console is None:
        console = Console()

    if not rungs:
        console.print("[dim]No unblocked rungs available.[/dim]")
        console.print("[dim]All active rungs are blocked or complete.[/dim]")
        return

    console.print(Text(header, style="bold yellow"))
    console.print()

    shown = rungs if limit is None else rungs[:limit]
    for i, rung in enumerate(shown, 1):
        effort_color = _effort_style(rung.effort.value)
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
        for opt in rung.options:
            mark, mark_style = ("✓", "bold green") if opt.chosen else ("○", "dim")
            line = Text("   ")
            line.append(f"{mark} ", style=mark_style)
            line.append(opt.text, style="green" if opt.chosen else "dim")
            console.print(line)
        console.print()


def render_validation(
    errors: list[str], warnings: list[str], console: Console | None = None
) -> None:
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


def _rung_css_class(rung: Rung) -> str:
    if rung.status == Status.BLOCKED:
        return "blocked"
    if rung.is_done:
        return "done"
    if rung.status == Status.IN_PROGRESS:
        return "in-progress"
    if rung.status == Status.EXPLORING:
        return "exploring"
    return "open"


def render_html(ladder: Ladder) -> str:
    """Render the ladder as a static, self-contained HTML page."""
    stages_html = []
    for stage in ladder.stages:
        rows = []
        for rung in stage.rungs:
            css = _rung_css_class(rung)
            effort = escape(rung.effort.value)
            row = [
                f'<li class="rung {css}">',
                '<div class="rung-head">',
                f'<span class="emoji">{escape(_status_emoji(rung.status))}</span>',
                f'<span class="id">{escape(rung.id)}</span>',
                f'<span class="title">{escape(rung.title)}</span>',
                f'<span class="effort {effort}">{effort}</span>',
                "</div>",
            ]
            if rung.why and not rung.is_done:
                row.append(f'<p class="why">{escape(rung.why)}</p>')
            if rung.blocked_by:
                row.append(
                    f'<p class="blocked-by">blocked by {escape(", ".join(rung.blocked_by))}</p>'
                )
            if rung.options:
                opts = "".join(
                    f'<li class="{"chosen" if o.chosen else ""}">'
                    f"{'✓' if o.chosen else '○'} {escape(o.text)}</li>"
                    for o in rung.options
                )
                row.append(f'<ul class="options">{opts}</ul>')
            row.append("</li>")
            rows.append("".join(row))

        stages_html.append(
            f'<section class="stage">'
            f'<h2><span class="dot">{escape(_stage_dot(stage))}</span> {escape(stage.name)}</h2>'
            f'<ul class="rungs">{"".join(rows)}</ul>'
            f"</section>"
        )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{escape(ladder.project)} — ladder</title>
<style>
  body {{ background: #0d1117; color: #c9d1d9; font: 15px/1.5 -apple-system, system-ui, sans-serif;
         max-width: 860px; margin: 0 auto; padding: 2.5rem 1.5rem; }}
  h1 {{ font-size: 1.3rem; margin: 0 0 .25rem; }}
  .summary {{ color: #8b949e; font-size: .9rem; margin-bottom: 2rem; }}
  h2 {{ font-size: 1rem; text-transform: lowercase; border-bottom: 1px solid #21262d;
       padding-bottom: .4rem; }}
  .dot {{ color: #8b949e; }}
  ul {{ list-style: none; padding: 0; margin: 0; }}
  .rungs {{ margin: .5rem 0 2rem; }}
  .rung {{ padding: .6rem 0; border-bottom: 1px solid #161b22; }}
  .rung-head {{ display: flex; align-items: baseline; gap: .6rem; }}
  .emoji {{ width: 1em; }}
  .id {{ color: #8b949e; font-size: .85rem; }}
  .title {{ flex: 1; }}
  .rung.done .title, .rung.blocked .title {{ color: #8b949e; text-decoration: line-through; }}
  .rung.in-progress .title {{ color: #d29922; font-weight: 600; }}
  .rung.exploring .title {{ color: #58a6ff; font-style: italic; }}
  .effort {{ font-size: .8rem; padding: 0 .2rem; }}
  .effort.small {{ color: #3fb950; }}
  .effort.medium {{ color: #d29922; }}
  .effort.large {{ color: #f85149; }}
  .why, .blocked-by {{ margin: .25rem 0 0 1.6em; color: #8b949e; font-size: .85rem;
       font-style: italic; }}
  .blocked-by {{ color: #f85149; font-style: normal; }}
  .options {{ margin: .35rem 0 0 1.6em; }}
  .options li {{ color: #8b949e; font-size: .85rem; }}
  .options li.chosen {{ color: #3fb950; }}
</style>
</head>
<body>
<h1>🪜 {escape(ladder.project)}</h1>
<p class="summary">v{ladder.version} &middot;
  {ladder.completed_count} done &middot;
  {ladder.in_progress_count} active &middot;
  {ladder.exploring_count} exploring &middot;
  {ladder.open_count} open &middot;
  {ladder.blocked_count} blocked</p>
{"".join(stages_html)}
</body>
</html>
"""
