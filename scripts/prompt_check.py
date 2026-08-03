#!/usr/bin/env python3
"""UserPromptSubmit hook: if this prompt is asking to see the ladder status/tree,
record what's expected so the Stop hook can verify the real command output
actually got pasted into the response, not just summarized."""

import json
import os
import re
import sys
import tempfile
from pathlib import Path

STATUS_TRIGGER = re.compile(
    r"show (the )?(full )?ladder\b"
    r"|what'?s on the ladder\b"
    r"|ladder status\b"
    r"|full status\b"
    r"|status full\b"
    r"|ladder tree\b"
    r"|show (the )?(full )?(ladder )?tree\b",
    re.IGNORECASE,
)
WANTS_TREE = re.compile(r"\btree\b", re.IGNORECASE)
WANTS_FULL = re.compile(r"\bfull\b", re.IGNORECASE)


def marker_path(session_id: str) -> Path:
    return Path(tempfile.gettempdir()) / f"ladder-expect-{session_id}.json"


def main() -> None:
    payload = json.load(sys.stdin)
    project_dir = Path(payload.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR", "."))
    if not (project_dir / ".ladder" / "ladder.md").exists():
        return

    user_input = payload.get("user_input") or ""
    if not STATUS_TRIGGER.search(user_input):
        return

    session_id = payload.get("session_id", "unknown")
    marker_path(session_id).write_text(
        json.dumps(
            {
                "cwd": str(project_dir),
                "command": "tree" if WANTS_TREE.search(user_input) else "status",
                "full": bool(WANTS_FULL.search(user_input)),
                "attempts": 0,
            }
        )
    )


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        assert STATUS_TRIGGER.search("show full ladder status")
        assert STATUS_TRIGGER.search("need the ladder status for the ladder project")
        assert STATUS_TRIGGER.search("what's on the ladder")
        assert STATUS_TRIGGER.search("show me the ladder tree")
        assert STATUS_TRIGGER.search("full status please")
        assert not STATUS_TRIGGER.search("fix the bug in parser.py")
        assert not STATUS_TRIGGER.search("what's the status of the deployment")
        print("ok")
        sys.exit(0)
    main()
