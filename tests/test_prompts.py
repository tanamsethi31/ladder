"""Guards against system.md (the universal, paste-into-any-AI prompt) silently
drifting out of sync with skills/ladder-tracking/SKILL.md (the Claude Code
plugin's copy) — exactly what happened before this test existed: SKILL.md
picked up a whole new rule (11, the hard "full" override) and a "Useful
commands" section across several commits, while system.md never did, leaving
non-Claude-Code users with strictly weaker protection against a failure mode
that was proven real."""

import re
from pathlib import Path

SYSTEM_MD = Path(__file__).parent.parent / "ladder" / "prompts" / "system.md"
SKILL_MD = Path(__file__).parent.parent / "skills" / "ladder-tracking" / "SKILL.md"

RULE_RE = re.compile(r"^\d+\.\s+\*\*", re.MULTILINE)


def test_same_number_of_numbered_rules() -> None:
    system_rules = len(RULE_RE.findall(SYSTEM_MD.read_text()))
    skill_rules = len(RULE_RE.findall(SKILL_MD.read_text()))
    assert system_rules == skill_rules, (
        f"system.md has {system_rules} numbered rules, SKILL.md has {skill_rules} — "
        "one was updated without the other. Sync them."
    )


def test_shared_command_line_mentions_every_command() -> None:
    system_text = SYSTEM_MD.read_text()
    skill_text = SKILL_MD.read_text()
    commands = [
        "ladder status",
        "ladder next",
        "ladder sprint",
        "ladder show",
        "ladder note",
        "ladder tree",
        "ladder export",
        "ladder scan",
    ]
    for cmd in commands:
        assert cmd in system_text, f"system.md is missing '{cmd}' — CLI commands page drifted"
        assert cmd in skill_text, f"SKILL.md is missing '{cmd}' — CLI commands page drifted"


def test_full_override_rule_present_in_both() -> None:
    # The specific rule that was actually missing when this test was written —
    # a direct regression test, not just the general count check above.
    for path in (SYSTEM_MD, SKILL_MD):
        text = path.read_text()
        assert "non-negotiable" in text, f"{path.name} is missing the 'full' override rule"
        assert "--no-color" in text, f"{path.name} is missing the --no-color note on rule 8"
