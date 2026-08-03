"""Tests for CLI commands."""

import json
from pathlib import Path

import pytest
from rich.console import Console
from typer.testing import CliRunner

import ladder.cli as cli_module
from ladder.cli import app
from ladder.core.parser import parse_ladder
from ladder.core.renderer import LADDER_THEME

runner = CliRunner()


@pytest.fixture(autouse=True)
def _isolated_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Run every test in its own empty directory, regardless of typer/click version."""
    monkeypatch.chdir(tmp_path)
    # --no-color reassigns the module-level console global; reset it so that
    # mutation doesn't leak into whichever test happens to run next.
    monkeypatch.setattr(cli_module, "console", Console(theme=LADDER_THEME))


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


def test_no_ladder_shows_helpful_error() -> None:
    # No `ladder init` here at all
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 1
    assert "No ladder found" in result.output
    assert "ladder init" in result.output


def test_init_twice_does_not_overwrite(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "--project", "Original"])
    result = runner.invoke(app, ["init", "--project", "Overwrite Attempt"])
    assert result.exit_code == 0
    assert "already exists" in result.output

    ladder = parse_ladder(Path(tmp_path, ".ladder", "ladder.md"))
    assert ladder.project == "Original"


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


def test_add_creates_new_stage_when_missing(tmp_path: Path) -> None:
    runner.invoke(app, ["init"])
    result = runner.invoke(app, ["add", "First billing task", "--stage", "billing"])
    assert result.exit_code == 0
    assert "Created new stage: billing" in result.output

    ladder = parse_ladder(Path(tmp_path, ".ladder", "ladder.md"))
    stage_names = [s.name for s in ladder.stages]
    assert "billing" in stage_names


def test_add_warns_on_nonexistent_blocker() -> None:
    runner.invoke(app, ["init"])
    result = runner.invoke(app, ["add", "Needs a blocker", "--blocked-by", "R999"])
    assert result.exit_code == 0
    assert "blocker R999 does not exist yet" in result.output


def test_add_warns_on_nonexistent_parent() -> None:
    runner.invoke(app, ["init"])
    result = runner.invoke(app, ["add", "Has a parent", "--parent", "R999"])
    assert result.exit_code == 0
    assert "parent R999 does not exist yet" in result.output


def test_add_prints_blocked_by_line_when_blockers_given() -> None:
    runner.invoke(app, ["init"])
    result = runner.invoke(app, ["add", "Blocked task", "--blocked-by", "R001"])
    assert result.exit_code == 0
    assert "Blocked by: R001" in result.output


def test_add_invalid_effort() -> None:
    runner.invoke(app, ["init"])
    result = runner.invoke(app, ["add", "Bad", "--effort", "huge"])
    assert result.exit_code == 1
    assert "Invalid effort" in result.output


def test_export(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "--project", "<Test & Co>"])
    result = runner.invoke(app, ["export"])
    assert result.exit_code == 0

    out = Path(tmp_path, ".ladder", "ladder.html")
    assert out.exists()
    html = out.read_text()
    assert "<Test & Co>" not in html  # must be escaped, not injected raw
    assert "&lt;Test &amp; Co&gt;" in html
    assert "R001" in html


def test_note() -> None:
    runner.invoke(app, ["init"])
    result = runner.invoke(app, ["note", "R001", "Watch out for X"])
    assert result.exit_code == 0

    ladder = parse_ladder(Path(".ladder", "ladder.md"))
    assert ladder.get_rung("R001").note == "Watch out for X"


def test_note_missing_rung() -> None:
    runner.invoke(app, ["init"])
    result = runner.invoke(app, ["note", "R999", "text"])
    assert result.exit_code == 1


def test_sprint_fits_budget() -> None:
    runner.invoke(app, ["init"])  # R001 small(1), R002 medium(2)
    result = runner.invoke(app, ["sprint", "--budget", "1"])
    assert result.exit_code == 0
    assert "R001" in result.output
    assert "R002" not in result.output


def test_sprint_default_budget_fits_both() -> None:
    runner.invoke(app, ["init"])
    result = runner.invoke(app, ["sprint"])
    assert result.exit_code == 0
    assert "R001" in result.output
    assert "R002" in result.output


def test_no_color_strips_ansi_even_with_force_color(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FORCE_COLOR", "3")
    runner.invoke(app, ["init"])
    result = runner.invoke(app, ["--no-color", "status"])
    assert result.exit_code == 0
    assert "\x1b[" not in result.output


def test_scan_flagged_exits_1() -> None:
    result = runner.invoke(app, ["scan", "We could either use Redis or Postgres."])
    assert result.exit_code == 1
    assert "may present an option" in result.output


def test_scan_clean_exits_0() -> None:
    result = runner.invoke(app, ["scan", "Fixed the bug in parser.py."])
    assert result.exit_code == 0
    assert result.output == ""


def test_scan_json_output() -> None:
    result = runner.invoke(app, ["--no-color", "scan", "--json", "Alternatively, cache it."])
    assert result.exit_code == 1
    data = json.loads(result.output)
    assert data["flagged"] is True
    assert data["reason"]


def test_scan_reads_stdin_when_no_arg() -> None:
    result = runner.invoke(app, ["scan"], input="Fixed the bug.")
    assert result.exit_code == 0


def test_scan_works_with_no_ladder(tmp_path: Path) -> None:
    # No `ladder init` here — scan must not require a ladder to exist
    result = runner.invoke(app, ["scan", "Done."])
    assert result.exit_code == 0


def test_next() -> None:
    runner.invoke(app, ["init"])
    # R001 and R002 exist from init
    result = runner.invoke(app, ["next"])
    assert result.exit_code == 0
    assert "R001" in result.output or "R002" in result.output


def test_next_reports_no_unblocked_rungs_and_their_blockers() -> None:
    runner.invoke(app, ["init"])
    runner.invoke(app, ["complete", "R001"])
    runner.invoke(app, ["complete", "R002"])
    # R003 and R004 block each other, so neither is ever unblocked.
    runner.invoke(app, ["add", "Needs R004", "--blocked-by", "R004"])
    runner.invoke(app, ["add", "Needs R003", "--blocked-by", "R003"])

    result = runner.invoke(app, ["next"])
    assert result.exit_code == 0
    assert "No unblocked rungs available" in result.output
    assert "waiting on dependencies" in result.output
    assert "R003 → blocked by R004" in result.output
    assert "R004 → blocked by R003" in result.output


def test_next_nudges_when_stage_half_done() -> None:
    runner.invoke(app, ["init"])
    runner.invoke(app, ["add", "Second foundation task", "--stage", "foundation"])
    runner.invoke(app, ["complete", "R001"])

    result = runner.invoke(app, ["next"])
    assert result.exit_code == 0
    assert "`foundation` is 1/2 done" in result.output
    assert "consider finishing it before moving on" in result.output


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


def _append_and_validate(tmp_path: Path, ladder_snippet: str) -> object:
    runner.invoke(app, ["init"])
    path = Path(tmp_path, ".ladder", "ladder.md")
    path.write_text(path.read_text() + ladder_snippet)
    return runner.invoke(app, ["validate"])


def test_validate_duplicate_id(tmp_path: Path) -> None:
    result = _append_and_validate(
        tmp_path,
        """
## dup

- [ ] **R001** — Duplicate of the init placeholder → *small*
""",
    )
    assert result.exit_code == 1
    assert "Duplicate rung ID: R001" in result.output


def test_validate_self_blocking(tmp_path: Path) -> None:
    result = _append_and_validate(
        tmp_path,
        """
## broken

- [ ] **R999** — Self blocker → *small*
  - Blocked by: R999
""",
    )
    assert result.exit_code == 1
    assert "cannot block itself" in result.output


def test_validate_circular_dependency(tmp_path: Path) -> None:
    result = _append_and_validate(
        tmp_path,
        """
## broken

- [ ] **R997** — First → *small*
  - Blocked by: R998
- [ ] **R998** — Second → *small*
  - Blocked by: R997
""",
    )
    assert result.exit_code == 1
    assert "Circular dependency" in result.output


def test_validate_orphaned_parent(tmp_path: Path) -> None:
    result = _append_and_validate(
        tmp_path,
        """
## broken

- [ ] **R999** — Orphan → *small*
  - Parent: R000
""",
    )
    assert result.exit_code == 1
    assert "parent 'R000' does not exist" in result.output


def test_validate_warning_done_but_no_option_chosen(tmp_path: Path) -> None:
    result = _append_and_validate(
        tmp_path,
        """
## warn

- [x] **R999** — Done but nothing picked → *small*
  - [ ] Option A
  - [ ] Option B
""",
    )
    assert result.exit_code == 0
    assert "marked done but no option chosen" in result.output


def test_validate_warning_done_but_still_blocked(tmp_path: Path) -> None:
    result = _append_and_validate(
        tmp_path,
        """
## warn

- [x] **R999** — Done but blocked → *small*
  - Blocked by: R001
""",
    )
    # Warnings alone don't fail the command
    assert result.exit_code == 0
    assert "is done but still lists blockers" in result.output


def test_validate_warning_blocked_status_no_blockers(tmp_path: Path) -> None:
    result = _append_and_validate(
        tmp_path,
        """
## warn

- [!] **R999** — Says blocked, lists nothing → *small*
""",
    )
    assert result.exit_code == 0
    assert "status is blocked but no blockers listed" in result.output


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


def test_abandon() -> None:
    runner.invoke(app, ["init"])
    result = runner.invoke(app, ["abandon", "R001", "--reason", "no longer needed"])
    assert result.exit_code == 0
    assert "Abandoned" in result.output

    ladder = parse_ladder(Path(".ladder", "ladder.md"))
    rung = ladder.get_rung("R001")
    assert rung is not None
    assert rung.note == "Abandoned: no longer needed"


@pytest.mark.parametrize("command", ["show", "do", "complete", "abandon", "explore", "reject"])
def test_single_rung_commands_report_not_found(command: str) -> None:
    runner.invoke(app, ["init"])
    result = runner.invoke(app, [command, "R999"])
    assert result.exit_code == 1
    assert "not found" in result.output


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


def test_prompt_prints_system_prompt() -> None:
    result = runner.invoke(app, ["prompt"])
    assert result.exit_code == 0
    assert "ladder" in result.output.lower()


def test_prompt_missing_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(cli_module, "__file__", str(tmp_path / "cli.py"))
    result = runner.invoke(app, ["prompt"])
    assert result.exit_code == 0
    assert "Prompt file not found" in result.output


def test_priority_sort_key_falls_back_when_rung_not_in_any_stage() -> None:
    from ladder.core.models import Effort, Ladder, Rung

    ladder = Ladder(project="test", stages=[])
    orphan = Rung(id="R999", title="orphan", effort=Effort.SMALL)
    assert cli_module._priority_sort_key(ladder, orphan) == (999, 0, "R999")
