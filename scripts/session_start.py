#!/usr/bin/env python3
"""SessionStart hook: if this project has a ladder, surface it and point at the skill."""

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ANSI_RE = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]")

project_dir = Path(os.environ.get("CLAUDE_PROJECT_DIR", "."))
ladder_file = project_dir / ".ladder" / "ladder.md"

if not ladder_file.exists() or shutil.which("ladder") is None:
    sys.exit(0)

env = dict(os.environ, NO_COLOR="1")
env.pop("FORCE_COLOR", None)
result = subprocess.run(
    ["ladder", "status"],
    cwd=project_dir,
    capture_output=True,
    text=True,
    timeout=10,
    env=env,
)
summary = next((line for line in result.stdout.splitlines() if line.strip()), "")
summary = ANSI_RE.sub("", summary)
if not summary:
    sys.exit(0)

context = (
    f"Ladder found in this project: {summary}\n\n"
    "Follow the ladder-tracking skill this session: read .ladder/ladder.md before "
    "presenting multiple options, and log new options/decisions as rungs as you go. "
    'If a question uses a vague reference ("that", "it", "the thing we were '
    "deciding\") that could match more than one open or exploring rung, don't guess "
    "which one before checking — run `ladder status`/`tree` and either name the one "
    "specific rung you're confident matches or ask which one."
)
print(
    json.dumps(
        {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": context}}
    )
)
