"""Deterministic, cheap checks over AI-assistant response text — no LLM call.

Provider-agnostic on purpose: any tool's hook/rule system (Claude Code, Cursor
rules, Copilot instructions, a raw shell script) can shell out to
`ladder scan` and reuse this instead of reimplementing it.
"""

from __future__ import annotations

import re

_SIGNAL_PATTERNS = [
    r"\b(?:option [ab12]\b|either .+ or |alternatively|we could instead|"
    r"another (?:option|approach|path)|you (?:could|might want to))\b",
]


def looks_like_unlogged_options(text: str) -> bool:
    """Cheap heuristic: does this text show signs of a presented option/decision
    that might not be logged? Explicit choice language only — deliberately does
    NOT fire on bare numbered/bulleted lists, which fired on ordinary structured
    notes (status recaps, step lists) far more often than on real choices."""
    return any(re.search(p, text, re.IGNORECASE) for p in _SIGNAL_PATTERNS)
