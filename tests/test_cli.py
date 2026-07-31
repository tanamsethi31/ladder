"""Tests for CLI commands."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from ladder.cli import app
from ladder.core.parser import parse_ladder

runner = CliRunner()


@pytest.fixture(autouse=True)
def _isolated_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Run every test in its own empty directory, regardless of typer/click version."""
    monkeypatch.chdir(tmp_path)


def test_init(tmp_path: Path) -> None:
    result = runner.invoke(app, ["init", "--project", "Test"])
    assert result.exit_code == 0
    assert "Created ladder" in result.output
    assert Path(tmp_path, ".ladder", "ladder.md").exists()


def test_status() -> None:
    runner.invoke(app, ["init"])
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "foundation" in result.output


def test_add(tmp_path: Path) -> None:
    runner.invoke(app, ["init"])
    result = runner.invoke(
        app,
        [
            "add",
            "New Feature",
            "--stage",
            "core",
            "--effort",
            "medium",
            "--context",
            "Testing add",
            "--why",
            "Because",
        ],
    )
    assert result.exit_code == 0
    assert "Added R003" in result.output

    # Verify it was written
    ladder = parse_ladder(Path(tmp_path, ".ladder", "ladder.md"))
    assert ladder.get_rung("R003") is not None
    assert ladder.get_rung("R003").title == "New Feature"


def test_add_invalid_effort() -> None:
    runner.invoke(app, ["init"])
    result = runner.invoke(app, ["add", "Bad", "--effort", "huge"])
    assert result.exit_code == 1
    assert "Invalid effort" in result.output


def test_next() -> None:
    runner.invoke(app, ["init"])
    # R001 and R002 exist from init
    result = runner.invoke(app, ["next"])
    assert result.exit_code == 0
    assert "R001" in result.output or "R002" in result.output


def test_validate_clean() -> None:
    runner.invoke(app, ["init"])
    result = runner.invoke(app, ["validate"])
    assert result.exit_code == 0
    assert "valid" in result.output


def test_validate_with_errors(tmp_path: Path) -> None:
    runner.invoke(app, ["init"])
    # Manually write a broken ladder
    path = Path(tmp_path, ".ladder", "ladder.md")
    content = path.read_text()
    # Add a rung with a non-existent blocker
    content += """
## broken

- [ ] **R999** — Bad → *small*
  - Context: bad
  - Blocked by: R999999
"""
    path.write_text(content)
    result = runner.invoke(app, ["validate"])
    assert result.exit_code == 1
    assert "does not exist" in result.output


def test_do_and_complete() -> None:
    runner.invoke(app, ["init"])
    result = runner.invoke(app, ["do", "R001"])
    assert result.exit_code == 0
    assert "working on" in result.output

    result = runner.invoke(app, ["complete", "R001"])
    assert result.exit_code == 0
    assert "Completed" in result.output


def test_explore_and_reject() -> None:
    runner.invoke(app, ["init"])
    result = runner.invoke(app, ["explore", "R001"])
    assert result.exit_code == 0
    assert "Exploring" in result.output

    result = runner.invoke(app, ["reject", "R001"])
    assert result.exit_code == 0
    assert "Rejected" in result.output


def test_show() -> None:
    runner.invoke(app, ["init"])
    result = runner.invoke(app, ["show", "R001"])
    assert result.exit_code == 0
    assert "R001" in result.output
    assert "scaffold" in result.output


def test_tree() -> None:
    runner.invoke(app, ["init"])
    result = runner.invoke(app, ["tree"])
    assert result.exit_code == 0
    assert "foundation" in result.output
