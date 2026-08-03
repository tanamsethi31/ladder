#!/usr/bin/env python3
"""Stop hook, two checks:

1. Status-relay enforcement: if a UserPromptSubmit hook (prompt_check.py) recorded
   that this turn was asked to show the ladder status/tree, re-run the real command
   now and verify its actual output shows up verbatim in what was said. If not,
   BLOCK the stop and force a redo — a plain reminder already proved unreliable in
   practice (rule 11 was worded as a hard, non-negotiable override and still got
   silently skipped in favor of a paraphrased summary).
2. Unlogged-options nudge: cheap regex heuristic, no LLM call, catches signs of an
   unlogged decision (lists, "either X or Y", "alternatively") and reminds mid-
   session instead of only at the end.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SIGNAL_PATTERNS = [
    r"(?:^|\n)\s*(?:[-*]|\d+[.)])\s+.+\n\s*(?:[-*]|\d+[.)])\s+.+",  # 2+ list items in a row
    r"\b(?:option [ab12]\b|either .+ or |alternatively|we could instead|"
    r"another (?:option|approach|path)|you (?:could|might want to))\b",
]
RUNG_ID_RE = re.compile(r"\bR\d{3,}\b")
MAX_BLOCK_ATTEMPTS = 3


def looks_like_unlogged_options(text: str) -> bool:
    return any(re.search(p, text, re.IGNORECASE) for p in SIGNAL_PATTERNS)


def _marker_path(session_id: str) -> Path:
    return Path(tempfile.gettempdir()) / f"ladder-expect-{session_id}.json"


def _run_ladder(cwd: str, command: str) -> str:
    env = dict(os.environ, NO_COLOR="1")
    env.pop("FORCE_COLOR", None)
    result = subprocess.run(
        ["ladder", "--no-color", command],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=10,
        env=env,
    )
    return result.stdout


def check_status_relay(payload: dict, message: str) -> str | None:
    """Return a block reason if the expected ladder output isn't actually in the
    response, or None if it's fine / not applicable / given up on retries."""
    session_id = payload.get("session_id", "unknown")
    marker = _marker_path(session_id)
    if not marker.exists() or shutil.which("ladder") is None:
        return None

    expect = json.loads(marker.read_text())
    real_output = _run_ladder(expect.get("cwd", "."), expect.get("command", "status"))
    header = next((line for line in real_output.splitlines() if line.strip()), "")

    missing_ids: set[str] = set()
    if expect.get("full") and header and header in message:
        missing_ids = set(RUNG_ID_RE.findall(real_output)) - set(RUNG_ID_RE.findall(message))

    if header and header in message and not missing_ids:
        marker.unlink(missing_ok=True)
        return None

    attempts = expect.get("attempts", 0) + 1
    if attempts > MAX_BLOCK_ATTEMPTS:
        marker.unlink(missing_ok=True)
        return None

    expect["attempts"] = attempts
    marker.write_text(json.dumps(expect))

    if not header or header not in message:
        return (
            f"The response was supposed to show the ladder's real `{expect.get('command')}` "
            "output but doesn't contain it verbatim. Run the command and paste its "
            "complete raw stdout in a code fence — do not summarize or paraphrase it."
        )
    return (
        '"full" was requested, so every rung must appear in the pasted output, but '
        f"these are missing: {', '.join(sorted(missing_ids))}. Paste the complete, "
        "untruncated output."
    )


def main() -> None:
    payload = json.load(sys.stdin)
    project_dir = Path(payload.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR", "."))
    if not (project_dir / ".ladder" / "ladder.md").exists():
        return

    message = payload.get("last_assistant_message") or ""

    block_reason = check_status_relay(payload, message)
    if block_reason:
        print(json.dumps({"decision": "block", "reason": block_reason}))
        return

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
