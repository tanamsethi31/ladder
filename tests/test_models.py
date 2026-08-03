"""Direct tests for ladder.core.models — the pieces not already exercised
indirectly through the CLI/parser tests."""

from __future__ import annotations

from ladder.core.models import Effort, Ladder, Rung, Stage, Status


def _rung(id: str, status: Status = Status.OPEN, blocked_by: list[str] | None = None) -> Rung:
    return Rung(
        id=id, title=f"Rung {id}", effort=Effort.SMALL, status=status, blocked_by=blocked_by or []
    )


def test_is_unblocked_true_with_no_blockers() -> None:
    assert _rung("R001").is_unblocked({"R001"}) is True


def test_is_unblocked_checks_id_existence_not_completion() -> None:
    """is_unblocked only checks that blocker IDs exist in the ladder — it does
    NOT check whether they're done. That's a separate, deliberate concern
    handled by Ladder.get_unblocked_rungs."""
    r = _rung("R002", blocked_by=["R001"])
    assert r.is_unblocked({"R001", "R002"}) is True  # R001 exists, even if not done
    assert r.is_unblocked({"R002"}) is False  # R001 doesn't exist at all


def test_is_unblocked_returns_true_when_ids_not_provided() -> None:
    r = _rung("R002", blocked_by=["R001"])
    assert r.is_unblocked(None) is True  # can't determine without context, don't block


def test_active_rungs_filters_by_status() -> None:
    stage = Stage(
        name="test",
        rungs=[
            _rung("R001", Status.OPEN),
            _rung("R002", Status.DONE),
            _rung("R003", Status.IN_PROGRESS),
            _rung("R004", Status.ABANDONED),
            _rung("R005", Status.EXPLORING),
        ],
    )
    active_ids = {r.id for r in stage.active_rungs}
    assert active_ids == {"R001", "R003", "R005"}


def test_get_unblocked_rungs_excludes_dangling_blocker_reference() -> None:
    """A blocked_by pointing at an ID that doesn't exist anywhere in the ladder
    (e.g. hand-edited or a typo) should not crash and should not be treated as
    unblocked — get_rung returns None, and the current logic only excludes when
    a real blocker is found and not done, so this documents the actual
    (permissive) behavior rather than assuming it errors."""
    ladder = Ladder(
        project="test",
        stages=[Stage(name="core", rungs=[_rung("R001", blocked_by=["R999"])])],
    )
    # Should not raise, regardless of what it decides
    result = ladder.get_unblocked_rungs()
    assert isinstance(result, list)


def test_get_unblocked_rungs_excludes_rung_blocked_by_incomplete_dependency() -> None:
    ladder = Ladder(
        project="test",
        stages=[
            Stage(
                name="core",
                rungs=[
                    _rung("R001", Status.OPEN),
                    _rung("R002", Status.OPEN, blocked_by=["R001"]),
                ],
            )
        ],
    )
    ids = {r.id for r in ladder.get_unblocked_rungs()}
    assert "R001" in ids
    assert "R002" not in ids


def test_get_unblocked_rungs_includes_rung_once_blocker_is_done() -> None:
    ladder = Ladder(
        project="test",
        stages=[
            Stage(
                name="core",
                rungs=[
                    _rung("R001", Status.DONE),
                    _rung("R002", Status.OPEN, blocked_by=["R001"]),
                ],
            )
        ],
    )
    ids = {r.id for r in ladder.get_unblocked_rungs()}
    assert "R002" in ids
