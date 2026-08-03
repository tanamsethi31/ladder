"""Tests for the ladder markdown parser and CLI logic."""

from pathlib import Path

from ladder.core.models import Effort, Rung, Status
from ladder.core.parser import generate_markdown, parse_ladder, write_ladder

SAMPLE_LADDER = """---
project: Test Project
version: 1
---

## foundation

- [x] **R001** — Scaffold → *small*
  - Context: Setting up
  - Why: Base layer
  - Blocked by: ~none~

## core

- [?] **R002** — Auth → *medium*
  - Context: Login system
  - Why: Security
  - [x] JWT
  - [ ] Session
  - Blocked by: ~none~
  - Status: exploring

- [!] **R003** — Database → *large*
  - Context: Storage
  - Why: Persistence
  - Blocked by: R002
  - Parent: R002

- [~] **R004** — Old approach → *small*
  - Context: Deprecated idea
  - Why: No longer needed
  - Status: abandoned
"""


def test_parse_ladder_with_new_statuses(tmp_path: Path) -> None:
    ladder_file = tmp_path / "ladder.md"
    ladder_file.write_text(SAMPLE_LADDER)

    ladder = parse_ladder(ladder_file)

    assert ladder.project == "Test Project"
    assert ladder.version == 1
    assert len(ladder.stages) == 2

    foundation = ladder.stages[0]
    assert foundation.name == "foundation"
    assert len(foundation.rungs) == 1
    assert foundation.rungs[0].id == "R001"
    assert foundation.rungs[0].status == Status.DONE
    assert foundation.rungs[0].effort == Effort.SMALL

    core = ladder.stages[1]
    assert core.name == "core"
    assert len(core.rungs) == 3

    r002 = core.rungs[0]
    assert r002.id == "R002"
    assert r002.status == Status.EXPLORING
    assert r002.effort == Effort.MEDIUM
    assert len(r002.options) == 2
    assert r002.options[0].chosen is True
    assert r002.options[1].chosen is False

    r003 = core.rungs[1]
    assert r003.id == "R003"
    assert r003.status == Status.BLOCKED
    assert r003.blocked_by == ["R002"]
    assert r003.parent == "R002"

    r004 = core.rungs[2]
    assert r004.id == "R004"
    assert r004.status == Status.ABANDONED


def test_in_progress_status_roundtrip(tmp_path: Path) -> None:
    ladder_file = tmp_path / "ladder.md"
    ladder_file.write_text(
        "---\nproject: Test\nversion: 1\n---\n\n"
        "## core\n\n"
        "- [▶] **R001** — Build the thing → *medium*\n"
        "  - Why: Doing it now\n"
    )

    ladder = parse_ladder(ladder_file)
    rung = ladder.get_rung("R001")
    assert rung is not None
    assert rung.status == Status.IN_PROGRESS

    # Round-trip: write it back out and re-parse - status must survive.
    write_ladder(ladder_file, ladder)
    reparsed_rung = parse_ladder(ladder_file).get_rung("R001")
    assert reparsed_rung is not None
    assert reparsed_rung.status == Status.IN_PROGRESS


def test_generate_and_roundtrip(tmp_path: Path) -> None:
    ladder_file = tmp_path / "ladder.md"
    ladder_file.write_text(SAMPLE_LADDER)

    ladder = parse_ladder(ladder_file)
    generated = generate_markdown(ladder)

    ladder_file.write_text(generated)
    ladder2 = parse_ladder(ladder_file)

    assert ladder2.project == ladder.project
    assert len(ladder2.stages) == len(ladder.stages)
    assert ladder2.stages[1].rungs[1].blocked_by == ["R002"]
    assert ladder2.stages[1].rungs[2].status == Status.ABANDONED


def test_next_rung_id(tmp_path: Path) -> None:
    ladder_file = tmp_path / "ladder.md"
    ladder_file.write_text(SAMPLE_LADDER)
    ladder = parse_ladder(ladder_file)

    assert ladder.next_rung_id() == "R005"

    # Add a rung and check again
    ladder.stages[0].rungs.append(Rung(id="R005", title="Test", effort=Effort.SMALL))
    assert ladder.next_rung_id() == "R006"


def test_get_unblocked_rungs(tmp_path: Path) -> None:
    ladder_file = tmp_path / "ladder.md"
    ladder_file.write_text(SAMPLE_LADDER)
    ladder = parse_ladder(ladder_file)

    unblocked = ladder.get_unblocked_rungs()
    # R001 is done, R002 is exploring, R003 is blocked by R002, R004 is abandoned
    # So only R002 should be unblocked and active
    ids = [r.id for r in unblocked]
    assert "R002" in ids
    assert "R003" not in ids  # blocked by R002 which is not done
    assert "R001" not in ids  # done
    assert "R004" not in ids  # abandoned


def test_stage_completeness(tmp_path: Path) -> None:
    ladder_file = tmp_path / "ladder.md"
    ladder_file.write_text(SAMPLE_LADDER)
    ladder = parse_ladder(ladder_file)

    assert ladder.stages[0].is_complete is True
    assert ladder.stages[1].is_complete is False
    assert ladder.completed_count == 1
    assert ladder.open_count == 0
    assert ladder.exploring_count == 1
    assert ladder.blocked_count == 1


def test_get_rung(tmp_path: Path) -> None:
    ladder_file = tmp_path / "ladder.md"
    ladder_file.write_text(SAMPLE_LADDER)
    ladder = parse_ladder(ladder_file)

    assert ladder.get_rung("R002") is not None
    assert ladder.get_rung("R002").title == "Auth"
    assert ladder.get_rung("R999") is None


def test_tolerant_parsing(tmp_path: Path) -> None:
    """Test that parser handles slight formatting variations."""
    tolerant = """---
project: Tolerant Test
version: 1
---

## core

- [ ] **R001** — Feature A → *small*
  - Context: testing tolerance
  - Why: because
  - [x] Option 1
  - [ ] Option 2
  - Blocked by: ~none~

- [x] **R002** — Feature B → *medium*
  - Context: another one
  - Why: reasons
"""
    ladder_file = tmp_path / "ladder.md"
    ladder_file.write_text(tolerant)
    ladder = parse_ladder(ladder_file)

    assert len(ladder.stages) == 1
    assert len(ladder.stages[0].rungs) == 2
    assert ladder.stages[0].rungs[0].status == Status.OPEN
    assert ladder.stages[0].rungs[1].status == Status.DONE


def test_invalid_status_metadata_falls_back_to_open(tmp_path: Path) -> None:
    """An AI assistant might write a Status value that doesn't map to any real
    status (typo, freeform text). Should fall back to open, not crash."""
    ladder_text = """---
project: Test
version: 1
---

## core

- [ ] **R001** — Feature A → *small*
  - Status: some-nonsense-value-nobody-wrote-correctly
"""
    ladder_file = tmp_path / "ladder.md"
    ladder_file.write_text(ladder_text)
    ladder = parse_ladder(ladder_file)
    assert ladder.stages[0].rungs[0].status == Status.OPEN


def test_invalid_version_in_frontmatter_falls_back_to_1(tmp_path: Path) -> None:
    ladder_text = """---
project: Test
version: not-a-number
---

## core

- [ ] **R001** — Feature A → *small*
"""
    ladder_file = tmp_path / "ladder.md"
    ladder_file.write_text(ladder_text)
    ladder = parse_ladder(ladder_file)
    assert ladder.version == 1
    assert ladder.project == "Test"


def test_metadata_lines_are_not_parsed_as_options(tmp_path: Path) -> None:
    """The option regex is loose enough to accidentally match a metadata line
    that starts with '- [ ]'-like text — must not create a bogus option."""
    ladder_text = """---
project: Test
version: 1
---

## core

- [ ] **R001** — Feature A → *small*
  - Context: some context
  - Why: some reason
  - [ ] Real option
  - Blocked by: ~none~
"""
    ladder_file = tmp_path / "ladder.md"
    ladder_file.write_text(ladder_text)
    ladder = parse_ladder(ladder_file)
    rung = ladder.stages[0].rungs[0]
    assert len(rung.options) == 1
    assert rung.options[0].text == "Real option"


def test_metadata_accidentally_written_as_a_checkbox_is_skipped(tmp_path: Path) -> None:
    """A plausible AI-formatting-drift case: metadata written with a checkbox
    prefix (e.g. "- [ ] Context: ...") instead of the plain "- Context: ..."
    form — the option regex would match it, so it must be filtered out."""
    ladder_text = """---
project: Test
version: 1
---

## core

- [ ] **R001** — Feature A → *small*
  - [ ] Context: this got checkbox-formatted by mistake
  - [ ] Real option
"""
    ladder_file = tmp_path / "ladder.md"
    ladder_file.write_text(ladder_text)
    ladder = parse_ladder(ladder_file)
    rung = ladder.stages[0].rungs[0]
    assert len(rung.options) == 1
    assert rung.options[0].text == "Real option"


def test_parent_and_note_fields_round_trip_through_write_and_parse(tmp_path: Path) -> None:
    ladder_text = """---
project: Test
version: 1
---

## core

- [ ] **R002** — Sub-task → *small*
  - Parent: R001
  - Note: a free-text note
"""
    ladder_file = tmp_path / "ladder.md"
    ladder_file.write_text(ladder_text)
    ladder = parse_ladder(ladder_file)
    assert ladder.stages[0].rungs[0].parent == "R001"
    assert ladder.stages[0].rungs[0].note == "a free-text note"

    out_path = tmp_path / "out.md"
    write_ladder(out_path, ladder)
    reparsed = parse_ladder(out_path)
    assert reparsed.stages[0].rungs[0].parent == "R001"
    assert reparsed.stages[0].rungs[0].note == "a free-text note"


def test_write_ladder(tmp_path: Path) -> None:
    ladder_file = tmp_path / "ladder.md"
    ladder_file.write_text(SAMPLE_LADDER)
    ladder = parse_ladder(ladder_file)

    new_path = tmp_path / "output.md"
    write_ladder(new_path, ladder)
    assert new_path.exists()
    content = new_path.read_text()
    assert "Test Project" in content
    assert "R002" in content
    assert "exploring" in content or "?" in content
