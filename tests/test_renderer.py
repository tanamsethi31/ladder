"""Tests for the small pure display-mapping functions in ladder.core.renderer —
cheap, fast, no I/O, previously entirely untested despite driving every visible
status indicator across the terminal and HTML renderers."""

from __future__ import annotations

from datetime import datetime

import pytest
from rich.console import Console

from ladder.core.models import Effort, Ladder, Option, Rung, Stage, Status
from ladder.core.renderer import (
    LADDER_THEME,
    _bold,
    _effort_style,
    _rung_css_class,
    _rung_style,
    _stage_dot,
    _stage_dot_css_class,
    _stage_dot_style,
    _status_emoji,
    render_html,
    render_next_suggestions,
    render_rung,
    render_status,
    render_tree,
    render_validation,
)


def _console() -> Console:
    return Console(theme=LADDER_THEME, record=True, width=100)


def _rung(status: Status) -> Rung:
    return Rung(id="R001", title="test", effort=Effort.SMALL, status=status)


@pytest.mark.parametrize(
    "status,expected",
    [
        (Status.DONE, "✓"),
        (Status.IN_PROGRESS, "▶"),
        (Status.EXPLORING, "?"),
        (Status.OPEN, "○"),
        (Status.BLOCKED, "✕"),
        (Status.ABANDONED, "~"),
        (Status.REJECTED, "~"),
    ],
)
def test_status_emoji(status: Status, expected: str) -> None:
    assert _status_emoji(status) == expected


@pytest.mark.parametrize(
    "effort,expected",
    [("small", "success"), ("medium", "warning"), ("large", "danger"), ("unknown", "white")],
)
def test_effort_style(effort: str, expected: str) -> None:
    assert _effort_style(effort) == expected


@pytest.mark.parametrize(
    "status,expected_style",
    [
        (Status.BLOCKED, "danger.dim"),
        (Status.ABANDONED, "dim strike"),
        (Status.REJECTED, "dim strike"),
        (Status.DONE, "dim strike"),
        (Status.IN_PROGRESS, "warning.bold"),
        (Status.EXPLORING, "info.italic"),
        (Status.OPEN, "white"),
    ],
)
def test_rung_style(status: Status, expected_style: str) -> None:
    assert _rung_style(_rung(status)) == expected_style


@pytest.mark.parametrize(
    "status,expected_class",
    [
        (Status.BLOCKED, "blocked"),
        (Status.DONE, "done"),
        (Status.ABANDONED, "done"),  # is_done covers abandoned too
        (Status.REJECTED, "done"),
        (Status.IN_PROGRESS, "in-progress"),
        (Status.EXPLORING, "exploring"),
        (Status.OPEN, "open"),
    ],
)
def test_rung_css_class(status: Status, expected_class: str) -> None:
    assert _rung_css_class(_rung(status)) == expected_class


def test_bold_uses_precombined_theme_entry_for_brand_colors() -> None:
    assert _bold("success") == "success.bold"
    assert _bold("warning") == "warning.bold"
    assert _bold("danger") == "danger.bold"


def test_bold_falls_back_to_concatenation_for_builtin_styles() -> None:
    assert _bold("dim") == "bold dim"
    assert _bold("white") == "bold white"


def _stage(rungs: list[Rung]) -> Stage:
    return Stage(name="test", rungs=rungs)


def test_stage_dot_all_done() -> None:
    stage = _stage([_rung(Status.DONE), _rung(Status.DONE)])
    assert _stage_dot(stage) == "●"
    assert _stage_dot_style(stage) == "success"
    assert _stage_dot_css_class(stage) == "complete"


def test_stage_dot_in_progress() -> None:
    stage = _stage([_rung(Status.DONE), _rung(Status.IN_PROGRESS)])
    assert _stage_dot(stage) == "◐"
    assert _stage_dot_style(stage) == "warning"
    assert _stage_dot_css_class(stage) == "progress"


def test_stage_dot_some_done_none_active() -> None:
    # ABANDONED counts as "done" too, so [DONE, ABANDONED] would be fully
    # complete — need an actually-open rung alongside a done one to hit the
    # any_done-but-not-complete-and-no-progress branch.
    stage = _stage([_rung(Status.DONE), _rung(Status.OPEN)])
    assert _stage_dot(stage) == "◑"
    assert _stage_dot_style(stage) == "warning"
    assert _stage_dot_css_class(stage) == "progress"


def test_stage_dot_nothing_started() -> None:
    stage = _stage([_rung(Status.OPEN), _rung(Status.OPEN)])
    assert _stage_dot(stage) == "○"
    assert _stage_dot_style(stage) == "dim"
    assert _stage_dot_css_class(stage) == ""


def _full_rung(**overrides: object) -> Rung:
    """A rung with every optional field populated, to exercise every
    conditional row/line across the render_* functions in one fixture."""
    defaults: dict[str, object] = {
        "id": "R001",
        "title": "Full rung",
        "effort": Effort.LARGE,
        "status": Status.IN_PROGRESS,
        "context": "some context",
        "why": "some reason",
        "options": [Option(text="Option A", chosen=True), Option(text="Option B", chosen=False)],
        "blocked_by": ["R002"],
        "parent": "R000",
        "note": "a note",
        "created_at": datetime(2026, 1, 1, 9, 0),
        "completed_at": datetime(2026, 1, 2, 10, 30),
    }
    defaults.update(overrides)
    return Rung(**defaults)  # type: ignore[arg-type]


def test_render_status_uses_default_console(capsys: pytest.CaptureFixture[str]) -> None:
    ladder = Ladder(project="Default Console Test", stages=[_stage([_rung(Status.OPEN)])])
    render_status(ladder)
    assert "Default Console Test" in capsys.readouterr().out


def test_render_status_filters_out_nonmatching_stage() -> None:
    ladder = Ladder(
        project="test",
        stages=[_stage([_rung(Status.OPEN)]), Stage(name="other", rungs=[_rung(Status.OPEN)])],
    )
    ladder.stages[0].name = "core"
    console = _console()
    render_status(ladder, console, filter_stage="core")
    output = console.export_text()
    assert "core" in output
    assert "other" not in output


def test_render_status_filters_out_stage_with_no_matching_effort() -> None:
    ladder = Ladder(
        project="test",
        stages=[Stage(name="core", rungs=[_rung(Status.OPEN)])],  # SMALL effort
    )
    console = _console()
    render_status(ladder, console, filter_effort="large")
    output = console.export_text()
    assert "core" not in output


def test_render_status_shows_blocked_by_why_and_options() -> None:
    ladder = Ladder(project="test", stages=[Stage(name="core", rungs=[_full_rung()])])
    console = _console()
    render_status(ladder, console)
    output = console.export_text()
    assert "blocked by R002" in output
    assert "some reason" in output
    assert "Option A" in output
    assert "Option B" in output


def test_render_tree_uses_default_console(capsys: pytest.CaptureFixture[str]) -> None:
    ladder = Ladder(project="Default Tree Test", stages=[_stage([_rung(Status.OPEN)])])
    render_tree(ladder)
    assert "Default Tree Test" in capsys.readouterr().out


def test_render_tree_title_with_square_brackets_is_not_swallowed_by_markup() -> None:
    """Regression: Tree.add() parses its string arg as Rich markup just like
    console.print, so a bare '[x]' in a title/why/option would otherwise
    vanish instead of rendering literally."""
    rung = _full_rung(title="Fix the [x]-checkbox bug", why="see [ref] for details")
    ladder = Ladder(project="test", stages=[Stage(name="core", rungs=[rung])])
    console = _console()
    render_tree(ladder, console)
    output = console.export_text()
    assert "Fix the [x]-checkbox bug" in output
    assert "see [ref] for details" in output


def test_render_tree_shows_blockers_parent_and_options() -> None:
    ladder = Ladder(project="test", stages=[Stage(name="core", rungs=[_full_rung()])])
    console = _console()
    render_tree(ladder, console)
    output = console.export_text()
    assert "blocked by R002" in output
    assert "parent: R000" in output
    assert "Option A" in output
    assert "Option B" in output


def test_render_rung_uses_default_console(capsys: pytest.CaptureFixture[str]) -> None:
    render_rung(_rung(Status.OPEN))
    assert "R001" in capsys.readouterr().out


def test_render_rung_shows_all_optional_fields() -> None:
    console = _console()
    render_rung(_full_rung(), console)
    output = console.export_text()
    assert "R000" in output  # parent
    assert "R002" in output  # blocked by
    assert "a note" in output
    assert "2026-01-02" in output  # completed_at
    assert "Options:" in output
    assert "[x] Option A" in output
    assert "[ ] Option B" in output


def test_render_rung_free_text_with_square_brackets_is_not_swallowed_by_markup() -> None:
    """Regression: Table cells parse plain string content as Rich markup too,
    so a bare '[...]' in context/why/note would otherwise vanish."""
    rung = _full_rung(context="see [notes] doc", why="blocked on [ref]", note="revisit [later]")
    console = _console()
    render_rung(rung, console)
    output = console.export_text()
    assert "see [notes] doc" in output
    assert "blocked on [ref]" in output
    assert "revisit [later]" in output


def test_render_next_suggestions_uses_default_console(capsys: pytest.CaptureFixture[str]) -> None:
    render_next_suggestions([_rung(Status.OPEN)])
    assert "Suggested next rungs" in capsys.readouterr().out


def test_render_next_suggestions_empty() -> None:
    console = _console()
    render_next_suggestions([], console)
    output = console.export_text()
    assert "No unblocked rungs available" in output
    assert "All active rungs are blocked or complete" in output


def test_render_next_suggestions_shows_unblock_hint_and_options() -> None:
    console = _console()
    render_next_suggestions([_full_rung()], console)
    output = console.export_text()
    assert "will unblock: R002" in output
    assert "Option A" in output
    assert "Option B" in output


def test_render_validation_uses_default_console(capsys: pytest.CaptureFixture[str]) -> None:
    render_validation([], [])
    assert "valid" in capsys.readouterr().out


def test_render_html_with_no_stages() -> None:
    html = render_html(Ladder(project="Empty"))
    assert "No stages yet" in html


def test_render_html_shows_blocked_by_and_options() -> None:
    ladder = Ladder(project="test", stages=[Stage(name="core", rungs=[_full_rung()])])
    html = render_html(ladder)
    assert "blocked by R002" in html
    assert '<li class="chosen">✓ Option A</li>' in html
    assert "○ Option B" in html
