"""Parse .ladder/ladder.md into structured Ladder models."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from ladder.core.models import (
    Effort,
    Ladder,
    Option,
    Rung,
    Stage,
    Status,
)

# More tolerant regex patterns
STAGE_RE = re.compile(r"^##\s+(.+)$", re.MULTILINE)
RUNG_RE = re.compile(
    r"^-\s*\[(.?)\]\s*\*\*(R\d+)\*\*\s*[—\-]\s*(.+?)\s*→\s*\*(small|medium|large)\*",
    re.MULTILINE | re.IGNORECASE,
)
OPTION_RE = re.compile(
    r"^\s+-\s*\[(.?)\]\s*(.+)$",
    re.MULTILINE,
)
META_RE = re.compile(
    r"^\s*-\s*(Context|Why|Blocked by|Parent|Note|Status):\s*(.+)$",
    re.MULTILINE | re.IGNORECASE,
)


def _extract_meta(text: str) -> dict[str, str]:
    """Extract metadata fields from rung body text."""
    meta: dict[str, str] = {}
    for match in META_RE.finditer(text):
        key = match.group(1).lower().replace(" ", "_")
        meta[key] = match.group(2).strip()
    return meta


def _extract_options(text: str) -> list[Option]:
    """Extract option checkboxes from rung body text."""
    options = []
    for match in OPTION_RE.finditer(text):
        checked = match.group(1).lower() == "x"
        option_text = match.group(2).strip()
        # Skip metadata lines that accidentally match
        if option_text.lower().startswith(
            ("context:", "why:", "blocked by:", "parent:", "note:", "status:")
        ):
            continue
        options.append(Option(text=option_text, chosen=checked))
    return options


def _parse_status(char: str, meta: dict[str, str]) -> Status:
    """Determine rung status from checkbox char and metadata."""
    char = char.lower()
    if char == "x":
        return Status.DONE
    if char == "~":
        return Status.ABANDONED
    if char == "!":
        return Status.BLOCKED
    if char == "?":
        return Status.EXPLORING
    if char == "▶":
        return Status.IN_PROGRESS
    # Check metadata override
    if "status" in meta:
        status_val = meta["status"].lower().replace(" ", "_")
        try:
            return Status(status_val)
        except ValueError:
            pass
    return Status.OPEN


def _parse_rung(match: re.Match[str], body_text: str) -> Rung:
    """Parse a single rung from regex match and body text."""
    check_char = match.group(1)
    rung_id = match.group(2)
    title = match.group(3).strip()
    effort = Effort(match.group(4).lower())

    meta = _extract_meta(body_text)
    options = _extract_options(body_text)
    status = _parse_status(check_char, meta)

    blocked_by = []
    if "blocked_by" in meta and meta["blocked_by"].lower() not in ("~none~", "none", ""):
        blocked_by = [b.strip() for b in meta["blocked_by"].split(",") if b.strip()]

    return Rung(
        id=rung_id,
        title=title,
        effort=effort,
        status=status,
        context=meta.get("context", ""),
        why=meta.get("why", ""),
        options=options,
        blocked_by=blocked_by,
        parent=meta.get("parent"),
        note=meta.get("note", ""),
        created_at=datetime.now(),
    )


def parse_ladder(path: Path) -> Ladder:
    """Parse a ladder.md file into a Ladder model."""
    content = path.read_text(encoding="utf-8")

    # Extract frontmatter
    project = "Untitled Project"
    version = 1
    if content.startswith("---"):
        front_end = content.find("---", 3)
        if front_end != -1:
            front = content[3:front_end].strip()
            for line in front.split("\n"):
                line = line.strip()
                if line.startswith("project:"):
                    project = line.split(":", 1)[1].strip()
                elif line.startswith("version:"):
                    try:
                        version = int(line.split(":", 1)[1].strip())
                    except ValueError:
                        version = 1
            content = content[front_end + 3 :]

    # Find stage boundaries
    stage_matches = list(STAGE_RE.finditer(content))
    stages: list[Stage] = []

    for i, match in enumerate(stage_matches):
        stage_name = match.group(1).strip().lower()
        start = match.end()
        end = stage_matches[i + 1].start() if i + 1 < len(stage_matches) else len(content)
        stage_text = content[start:end]

        rungs: list[Rung] = []
        for rung_match in RUNG_RE.finditer(stage_text):
            rung_start = rung_match.start()
            next_rung = RUNG_RE.search(stage_text, rung_match.end())
            rung_end = next_rung.start() if next_rung else len(stage_text)
            body_text = stage_text[rung_start:rung_end]
            rungs.append(_parse_rung(rung_match, body_text))

        stages.append(Stage(name=stage_name, rungs=rungs))

    return Ladder(project=project, version=version, stages=stages)


def generate_markdown(ladder: Ladder) -> str:
    """Generate a ladder.md string from a Ladder model."""
    lines = [
        "---",
        f"project: {ladder.project}",
        f"version: {ladder.version}",
        "---",
        "",
    ]

    for stage in ladder.stages:
        lines.append(f"## {stage.name}")
        lines.append("")
        for rung in stage.rungs:
            check = {
                Status.DONE: "x",
                Status.ABANDONED: "~",
                Status.BLOCKED: "!",
                Status.EXPLORING: "?",
                Status.IN_PROGRESS: "▶",
                Status.REJECTED: "~",
            }.get(rung.status, " ")
            lines.append(f"- [{check}] **{rung.id}** — {rung.title} → *{rung.effort.value}*")
            if rung.context:
                lines.append(f"  - Context: {rung.context}")
            if rung.why:
                lines.append(f"  - Why: {rung.why}")
            for opt in rung.options:
                opt_check = "x" if opt.chosen else " "
                lines.append(f"  - [{opt_check}] {opt.text}")
            if rung.blocked_by:
                lines.append(f"  - Blocked by: {', '.join(rung.blocked_by)}")
            elif rung.options and not rung.blocked_by:
                lines.append("  - Blocked by: ~none~")
            if rung.parent:
                lines.append(f"  - Parent: {rung.parent}")
            if rung.note:
                lines.append(f"  - Note: {rung.note}")
            if rung.status not in (Status.OPEN, Status.DONE):
                lines.append(f"  - Status: {rung.status.value}")
            lines.append("")

    return "\n".join(lines)


def write_ladder(path: Path, ladder: Ladder) -> None:
    """Write a Ladder model back to ladder.md."""
    path.write_text(generate_markdown(ladder), encoding="utf-8")
