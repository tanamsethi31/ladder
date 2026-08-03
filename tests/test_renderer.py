"""Tests for the small pure display-mapping functions in ladder.core.renderer —
cheap, fast, no I/O, previously entirely untested despite driving every visible
status indicator across the terminal and HTML renderers."""

from __future__ import annotations

import pytest

from ladder.core.models import Effort, Rung, Stage, Status
from ladder.core.renderer import (
    _bold,
    _effort_style,
    _rung_css_class,
    _rung_style,
    _stage_dot,
    _stage_dot_css_class,
    _stage_dot_style,
    _status_emoji,
)


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
