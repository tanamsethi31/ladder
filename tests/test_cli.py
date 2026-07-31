"""Tests for CLI commands."""

from pathlib import Path

from typer.testing import CliRunner

from ladder.cli import app
from ladder.core.parser import parse_ladder

runner = CliRunner()


def test_init() -> None:
    with runner.isolated_filesystem() as td:
        result = runner.invoke(app, ["init", "--project", "Test"])
        assert result.exit_code == 0
        assert "Created ladder" in result.output
        assert Path(td, ".ladder", "ladder.md").exists()


def test_status() -> None:
    with runner.isolated_filesystem():
        runner.invoke(app, ["init"])
        result = runner.invoke(app, ["status"])
        assert result.exit_code == 0
        assert "foundation" in result.output


def test_add() -> None:
    with runner.isolated_filesystem() as td:
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
        ladder = parse_ladder(Path(td, ".ladder", "ladder.md"))
        assert ladder.get_rung("R003") is not None
        assert ladder.get_rung("R003").title == "New Feature"


def test_add_invalid_effort() -> None:
    with runner.isolated_filesystem():
        runner.invoke(app, ["init"])
        result = runner.invoke(app, ["add", "Bad", "--effort", "huge"])
        assert result.exit_code == 1
        assert "Invalid effort" in result.output


def test_next() -> None:
    with runner.isolated_filesystem():
        runner.invoke(app, ["init"])
        # R001 and R002 exist from init
        result = runner.invoke(app, ["next"])
        assert result.exit_code == 0
        assert "R001" in result.output or "R002" in result.output


def test_validate_clean() -> None:
    with runner.isolated_filesystem():
        runner.invoke(app, ["init"])
        result = runner.invoke(app, ["validate"])
        assert result.exit_code == 0
        assert "valid" in result.output


def test_validate_with_errors() -> None:
    with runner.isolated_filesystem() as td:
        runner.invoke(app, ["init"])
        # Manually write a broken ladder
        path = Path(td, ".ladder", "ladder.md")
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
    with runner.isolated_filesystem():
        runner.invoke(app, ["init"])
        result = runner.invoke(app, ["do", "R001"])
        assert result.exit_code == 0
        assert "working on" in result.output

        result = runner.invoke(app, ["complete", "R001"])
        assert result.exit_code == 0
        assert "Completed" in result.output


def test_explore_and_reject() -> None:
    with runner.isolated_filesystem():
        runner.invoke(app, ["init"])
        result = runner.invoke(app, ["explore", "R001"])
        assert result.exit_code == 0
        assert "Exploring" in result.output

        result = runner.invoke(app, ["reject", "R001"])
        assert result.exit_code == 0
        assert "Rejected" in result.output


def test_show() -> None:
    with runner.isolated_filesystem():
        runner.invoke(app, ["init"])
        result = runner.invoke(app, ["show", "R001"])
        assert result.exit_code == 0
        assert "R001" in result.output
        assert "scaffold" in result.output


def test_tree() -> None:
    with runner.isolated_filesystem():
        runner.invoke(app, ["init"])
        result = runner.invoke(app, ["tree"])
        assert result.exit_code == 0
        assert "foundation" in result.output
