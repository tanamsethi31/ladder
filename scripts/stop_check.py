#!/usr/bin/env python3
"""Stop hook: nudge if the just-finished turn looks like it presented options or a
decision point that might not be logged yet. Cheap regex heuristic, no LLM call, so
it's free to run after every single turn (Stop fires on every turn, no matcher)."""

import json
import os
import re
import sys
from pathlib import Path

SIGNAL_PATTERNS = [
    r"(?:^|\n)\s*(?:[-*]|\d+[.)])\s+.+\n\s*(?:[-*]|\d+[.)])\s+.+",  # 2+ list items in a row
    r"\b(?:option [ab12]\b|either .+ or |alternatively|we could instead|"
    r"another (?:option|approach|path)|you (?:could|might want to))\b",
]


def looks_like_unlogged_options(text: str) -> bool:
    return any(re.search(p, text, re.IGNORECASE) for p in SIGNAL_PATTERNS)


def main() -> None:
    payload = json.load(sys.stdin)
    project_dir = Path(payload.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR", "."))
    if not (project_dir / ".ladder" / "ladder.md").exists():
        return

    message = payload.get("last_assistant_message") or ""
    if not looks_like_unlogged_options(message):
        return

    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "Stop",
                    "additionalContext": (
                        "This response may have presented multiple options or a "
                        "decision point. Per the ladder-tracking skill: if these "
                        "aren't logged in .ladder/ladder.md yet, log them now (or "
                        "note briefly why they don't need to be)."
                    ),
                }
            }
        )
    )


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        assert looks_like_unlogged_options("- Option A\n- Option B") is True
        assert looks_like_unlogged_options("1. do this\n2. do that") is True
        assert looks_like_unlogged_options("We could either use Redis or Postgres.")
        assert looks_like_unlogged_options("Alternatively, we could cache it.")
        assert looks_like_unlogged_options("Fixed the bug in parser.py, line 42.") is False
        assert looks_like_unlogged_options("Done. Tests pass.") is False
        print("ok")
        sys.exit(0)
    main()
