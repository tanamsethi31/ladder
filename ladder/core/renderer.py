"""Rich terminal rendering for the ladder."""

from __future__ import annotations

from html import escape

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.theme import Theme
from rich.tree import Tree

from ladder.core.models import Ladder, Rung, Stage, Status

# Brand palette: warm amber/wood tones tied to the 🪜 theme, not a generic
# blue-on-near-black dev-tool look. Named so the palette has one source of
# truth instead of hex scattered through every style string.
# Rich can't resolve "bold <theme-name>" built from string concatenation at
# render time, so bold/dim/italic variants are pre-combined here instead.
LADDER_THEME = Theme(
    {
        "success": "#93b854",
        "success.bold": "bold #93b854",
        "warning": "#e0a458",
        "warning.bold": "bold #e0a458",
        "danger": "#d0604f",
        "danger.bold": "bold #d0604f",
        "danger.dim": "dim #d0604f",
        "info": "#6fa3a0",
        "info.bold": "bold #6fa3a0",
        "info.italic": "italic #6fa3a0",
    }
)

_BOLD_VARIANT = {"success": "success.bold", "warning": "warning.bold", "danger": "danger.bold"}


def _bold(style_name: str) -> str:
    """A bold variant of a style name, using a pre-combined theme entry for our
    custom brand colors (Rich can't resolve "bold <theme-name>" from a
    concatenated string at render time)."""
    return _BOLD_VARIANT.get(style_name, f"bold {style_name}")


def _effort_style(effort: str) -> str:
    return {
        "small": "success",
        "medium": "warning",
        "large": "danger",
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


def _stage_dot_style(stage: Stage) -> str:
    if stage.is_complete:
        return "success"
    if stage.has_progress or stage.any_done:
        return "warning"
    return "dim"


def _rung_style(rung: Rung) -> str:
    if rung.status == Status.BLOCKED:
        return "danger.dim"
    if rung.status == Status.ABANDONED or rung.status == Status.REJECTED:
        return "dim strike"
    if rung.is_done:
        return "dim strike"
    if rung.status == Status.IN_PROGRESS:
        return "warning.bold"
    if rung.status == Status.EXPLORING:
        return "info.italic"
    return "white"


def render_status(
    ladder: Ladder,
    console: Console | None = None,
    filter_stage: str | None = None,
    filter_effort: str | None = None,
) -> None:
    """Render the full ladder status to the terminal."""
    if console is None:
        console = Console(theme=LADDER_THEME)

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
        Text(str(ladder.completed_count), style="success.bold", justify="center"),
        Text(str(ladder.in_progress_count), style="warning.bold", justify="center"),
        Text(str(ladder.exploring_count), style="info.bold", justify="center"),
        Text(str(ladder.open_count), style="bold white", justify="center"),
        Text(str(ladder.blocked_count), style="danger.bold", justify="center"),
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
        dot_style = _stage_dot_style(stage)

        console.print(Text(f"{dot} {stage.name}", style=_bold(dot_style)))
        console.print()
        console.print(_render_rung_table(visible_rungs))
        console.print()


def _render_rung_table(rungs: list[Rung]) -> Table:
    """A table of rungs, one row each, with alternative options nested inside the row."""
    table = Table(box=box.SIMPLE_HEAD, show_edge=False, pad_edge=False, expand=True)
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
            body.append(f"  [blocked by {', '.join(rung.blocked_by)}]", style="danger.dim")

        if rung.why and not rung.is_done:
            body.append("\n   ")
            body.append(rung.why, style="dim italic")

        for opt in rung.options:
            body.append("\n   ")
            if opt.chosen:
                body.append("✓ ", style="success.bold")
                body.append(opt.text, style="success")
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
        console = Console(theme=LADDER_THEME)

    root = Tree(f"🪜 [bold]{ladder.project}[/bold]")

    for stage in ladder.stages:
        dot = _stage_dot(stage)
        dot_style = _stage_dot_style(stage)
        stage_node = root.add(f"[{dot_style}]{dot}[/{dot_style}] [bold]{stage.name}[/bold]")
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
                rung_node.add(f"[danger]← blocked by {blockers}[/danger]")
            if rung.parent:
                rung_node.add(f"[dim]← parent: {rung.parent}[/dim]")
            if rung.why:
                rung_node.add(f"[dim italic]↳ {rung.why}[/dim italic]")
            for opt in rung.options:
                mark = "[success.bold]✓[/success.bold]" if opt.chosen else "[dim]○[/dim]"
                text_style = "success" if opt.chosen else "dim"
                rung_node.add(f"{mark} [{text_style}]{opt.text}[/{text_style}]")

    console.print(root)


def render_rung(rung: Rung, console: Console | None = None) -> None:
    """Render a single rung in detail."""
    if console is None:
        console = Console(theme=LADDER_THEME)

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
            style = "success" if opt.chosen else "white"
            console.print(f"  {check} {opt.text}", style=style)


def render_next_suggestions(
    rungs: list[Rung],
    console: Console | None = None,
    limit: int | None = 5,
    header: str = "🎯 Suggested next rungs",
) -> None:
    """Render suggested next rungs."""
    if console is None:
        console = Console(theme=LADDER_THEME)

    if not rungs:
        console.print("[dim]No unblocked rungs available.[/dim]")
        console.print("[dim]All active rungs are blocked or complete.[/dim]")
        return

    console.print(Text(header, style="warning.bold"))
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
            mark, mark_style = ("✓", "success.bold") if opt.chosen else ("○", "dim")
            line = Text("   ")
            line.append(f"{mark} ", style=mark_style)
            line.append(opt.text, style="success" if opt.chosen else "dim")
            console.print(line)
        console.print()


def render_validation(
    errors: list[str], warnings: list[str], console: Console | None = None
) -> None:
    """Render validation results."""
    if console is None:
        console = Console(theme=LADDER_THEME)

    if not errors and not warnings:
        console.print("[success]✓[/success] Ladder is valid. No issues found.")
        return

    if errors:
        console.print(Text(f"✕ {len(errors)} error(s) found:", style="danger.bold"))
        for err in errors:
            console.print(f"  [danger]•[/danger] {err}")
        console.print()

    if warnings:
        console.print(Text(f"⚠ {len(warnings)} warning(s) found:", style="warning.bold"))
        for warn in warnings:
            console.print(f"  [warning]•[/warning] {warn}")


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


def _stage_dot_css_class(stage: Stage) -> str:
    if stage.is_complete:
        return "complete"
    if stage.has_progress:
        return "progress"
    if stage.any_done:
        return "progress"
    return ""


_FAVICON = (
    "data:image/svg+xml,"
    "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'>"
    "<text y='.9em' font-size='90'>%F0%9F%AA%9C</text></svg>"
)


def render_html(ladder: Ladder) -> str:
    """Render the ladder as a static, self-contained HTML page."""
    if not ladder.stages:
        stages_html = (
            '<p class="empty">No stages yet. Run <code>ladder add "First feature"</code> '
            "to get started.</p>"
        )
    else:
        sections = []
        for stage in ladder.stages:
            total = len(stage.rungs)
            done = sum(1 for r in stage.rungs if r.is_done)
            percent = round(100 * done / total) if total else 0

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

            sections.append(
                f'<details class="stage"{" open" if not stage.is_complete else ""}>'
                f'<summary><span class="dot {_stage_dot_css_class(stage)}">'
                f"{escape(_stage_dot(stage))}</span> "
                f'<span class="stage-name">{escape(stage.name)}</span>'
                f'<span class="stage-count">{done}/{total}</span></summary>'
                f'<div class="bar"><div class="bar-fill" style="width:{percent}%"></div></div>'
                f'<ul class="rungs">{"".join(rows)}</ul>'
                f"</details>"
            )
        stages_html = "".join(sections)

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="{escape(ladder.project)} — decision ladder, exported from Ladder">
<link rel="icon" href="{_FAVICON}">
<title>{escape(ladder.project)} — ladder</title>
<style>
  :root {{
    --bg: #181310; --surface: #221b16; --border: #362c23; --text: #efe4d3; --dim: #a89a86;
    --green: #93b854; --yellow: #e0a458; --red: #d0604f; --blue: #6fa3a0;
  }}
  @media (prefers-color-scheme: light) {{
    :root {{
      --bg: #f7f1e6; --surface: #fffdf8; --border: #ddd0ba; --text: #2b2118; --dim: #6f6252;
      --green: #4d6820; --yellow: #8a5c14; --red: #a8402f; --blue: #3f7370;
    }}
  }}
  * {{ box-sizing: border-box; }}
  body {{
    background: var(--bg); color: var(--text);
    font: 15px/1.6 ui-sans-serif, -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    font-variant-numeric: tabular-nums;
    max-width: 780px; margin: 0 auto; padding: 3rem 1.5rem 4rem;
  }}
  h1 {{
    font-size: 1.6rem; font-weight: 700; letter-spacing: -0.02em; margin: 0 0 .35rem;
    text-wrap: balance;
  }}
  .stats {{
    display: flex; gap: 1px; background: var(--border); border: 1px solid var(--border);
    border-radius: 8px; overflow: hidden; margin: 1.25rem 0 2.25rem;
  }}
  .stat {{ flex: 1; background: var(--surface); padding: .6rem .5rem; text-align: center; }}
  .stat b {{ display: block; font-size: 1.15rem; font-weight: 700; }}
  .stat span {{ color: var(--dim); font-size: .72rem; text-transform: uppercase;
       letter-spacing: .04em; }}
  .stat.done b {{ color: var(--green); }}
  .stat.active b {{ color: var(--yellow); }}
  .stat.exploring b {{ color: var(--blue); }}
  .stat.blocked b {{ color: var(--red); }}
  .empty {{ color: var(--dim); }}
  details.stage {{ margin-bottom: 1.5rem; }}
  summary {{
    display: flex; align-items: baseline; gap: .5rem; cursor: pointer; list-style: none;
    padding-bottom: .5rem; border-bottom: 1px solid var(--border);
    font-weight: 600; font-size: .95rem;
  }}
  summary::-webkit-details-marker {{ display: none; }}
  .dot {{ color: var(--dim); }}
  .dot.complete {{ color: var(--green); }}
  .dot.progress {{ color: var(--yellow); }}
  .stage-name {{ text-transform: lowercase; flex: 1; }}
  .stage-count {{ color: var(--dim); font-weight: 400; font-size: .8rem; }}
  .bar {{ height: 3px; background: var(--border); margin-top: -1px; }}
  .bar-fill {{ height: 100%; background: var(--green); transition: width .2s; }}
  ul {{ list-style: none; padding: 0; margin: 0; }}
  .rungs {{ margin-top: .25rem; }}
  .rung {{
    padding: .65rem .4rem; border-bottom: 1px solid var(--border); border-radius: 6px;
    transition: background .15s;
  }}
  .rung:hover {{ background: var(--surface); }}
  .rung-head {{ display: flex; align-items: baseline; gap: .6rem; }}
  .emoji {{ width: 1em; }}
  .id {{ color: var(--dim); font-size: .82rem; font-variant-numeric: tabular-nums; }}
  .title {{ flex: 1; }}
  .rung.done .title {{ color: var(--dim); text-decoration: line-through; }}
  .rung.blocked .title {{ color: var(--red); }}
  .rung.in-progress .title {{ color: var(--yellow); font-weight: 600; }}
  .rung.exploring .title {{ color: var(--blue); font-style: italic; }}
  .effort {{ font-size: .78rem; padding: 0 .2rem; font-weight: 500; }}
  .effort.small {{ color: var(--green); }}
  .effort.medium {{ color: var(--yellow); }}
  .effort.large {{ color: var(--red); }}
  .why, .blocked-by {{
    margin: .3rem 0 0 1.6em; color: var(--dim); font-size: .85rem; font-style: italic;
  }}
  .blocked-by {{ color: var(--red); font-style: normal; }}
  .options {{ margin: .4rem 0 0 1.6em; }}
  .options li {{ color: var(--dim); font-size: .85rem; }}
  .options li.chosen {{ color: var(--green); }}
</style>
</head>
<body>
<h1>🪜 {escape(ladder.project)}</h1>
<div class="stats">
  <div class="stat done"><b>{ladder.completed_count}</b><span>done</span></div>
  <div class="stat active"><b>{ladder.in_progress_count}</b><span>active</span></div>
  <div class="stat exploring"><b>{ladder.exploring_count}</b><span>exploring</span></div>
  <div class="stat"><b>{ladder.open_count}</b><span>open</span></div>
  <div class="stat blocked"><b>{ladder.blocked_count}</b><span>blocked</span></div>
</div>
{stages_html}
</body>
</html>
"""
