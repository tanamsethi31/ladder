"""Pydantic models for the ladder data format."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Effort(str, Enum):
    """Effort estimate for a rung."""

    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


class Status(str, Enum):
    """Status of a rung."""

    OPEN = "open"
    EXPLORING = "exploring"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    ABANDONED = "abandoned"
    BLOCKED = "blocked"
    REJECTED = "rejected"


class Option(BaseModel):
    """A single option within a rung."""

    text: str
    chosen: bool = False


class Rung(BaseModel):
    """A single rung on the ladder — one decision point."""

    id: str = Field(..., pattern=r"^R\d{3,}$")
    title: str
    effort: Effort = Effort.MEDIUM
    status: Status = Status.OPEN
    context: str = ""
    why: str = ""
    options: list[Option] = Field(default_factory=list)
    blocked_by: list[str] = Field(default_factory=list)
    # Optional[X], not X | None: pydantic evals these at class-definition time
    # even with `from __future__ import annotations`, which breaks on Python <3.10.
    parent: Optional[str] = None  # noqa: UP045
    note: str = ""
    created_at: Optional[datetime] = None  # noqa: UP045
    completed_at: Optional[datetime] = None  # noqa: UP045

    @property
    def is_done(self) -> bool:
        return self.status in (Status.DONE, Status.ABANDONED, Status.REJECTED)

    @property
    def is_active(self) -> bool:
        return self.status in (Status.OPEN, Status.EXPLORING, Status.IN_PROGRESS)

    def is_unblocked(self, all_rung_ids: set[str] | None = None) -> bool:
        """Check that every blocker ID actually refers to a rung in the ladder
        (dangling references aside, not that those rungs are done — for that,
        see Ladder.get_unblocked_rungs, which checks completion separately)."""
        if not self.blocked_by:
            return True
        if all_rung_ids is None:
            return True  # cannot determine without full context
        return all(blocker in all_rung_ids for blocker in self.blocked_by)


class Stage(BaseModel):
    """A stage groups related rungs vertically."""

    name: str
    rungs: list[Rung] = Field(default_factory=list)

    @property
    def is_complete(self) -> bool:
        return len(self.rungs) > 0 and all(r.is_done for r in self.rungs)

    @property
    def has_progress(self) -> bool:
        return any(r.status in (Status.IN_PROGRESS, Status.EXPLORING) for r in self.rungs)

    @property
    def any_done(self) -> bool:
        return any(r.is_done for r in self.rungs)

    @property
    def active_rungs(self) -> list[Rung]:
        return [r for r in self.rungs if r.is_active]


class Ladder(BaseModel):
    """The full project ladder."""

    project: str = "Untitled Project"
    version: int = 1
    stages: list[Stage] = Field(default_factory=list)

    @property
    def all_rungs(self) -> list[Rung]:
        return [rung for stage in self.stages for rung in stage.rungs]

    @property
    def all_rung_ids(self) -> set[str]:
        return {r.id for r in self.all_rungs}

    @property
    def completed_count(self) -> int:
        return sum(1 for r in self.all_rungs if r.status == Status.DONE)

    @property
    def in_progress_count(self) -> int:
        return sum(1 for r in self.all_rungs if r.status == Status.IN_PROGRESS)

    @property
    def exploring_count(self) -> int:
        return sum(1 for r in self.all_rungs if r.status == Status.EXPLORING)

    @property
    def open_count(self) -> int:
        return sum(1 for r in self.all_rungs if r.status == Status.OPEN)

    @property
    def blocked_count(self) -> int:
        return sum(1 for r in self.all_rungs if r.status == Status.BLOCKED)

    def get_rung(self, rung_id: str) -> Rung | None:
        for rung in self.all_rungs:
            if rung.id == rung_id:
                return rung
        return None

    def next_rung_id(self) -> str:
        """Generate the next available rung ID."""
        existing = sorted(
            [int(r.id[1:]) for r in self.all_rungs if r.id.startswith("R") and r.id[1:].isdigit()],
            reverse=True,
        )
        next_num = (existing[0] + 1) if existing else 1
        return f"R{next_num:03d}"

    def get_unblocked_rungs(self) -> list[Rung]:
        """Return all rungs that are not blocked by incomplete dependencies."""
        all_ids = self.all_rung_ids
        result = []
        for rung in self.all_rungs:
            if rung.is_active and rung.is_unblocked(all_ids):
                # Check if blockers are actually done
                blocked = False
                for blocker_id in rung.blocked_by:
                    blocker = self.get_rung(blocker_id)
                    if blocker and not blocker.is_done:
                        blocked = True
                        break
                if not blocked:
                    result.append(rung)
        return result
