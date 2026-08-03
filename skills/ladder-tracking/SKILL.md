---
name: ladder-tracking
description: Use when this project has a .ladder/ladder.md file, or the user asks to track/log a decision, says "ladder do R###", "log that", "track this", "ladder status full"/"full status", or wants to see the ladder/status/tree. Governs how to read and update the project's decision ladder.
---

# Ladder Tracking

We track this project's decision ladder in `.ladder/ladder.md`. Every time multiple
paths present themselves during a session, one gets picked and the others normally
vanish into scrollback — the ladder captures them instead.

## Rules

1. **Before presenting multiple options**, read `.ladder/ladder.md` if it exists.
2. **When you present options**, append them to the current stage as a new rung.
3. **Format each rung exactly:**
   ```
   - [ ] **R###** — Title → *effort*
     - Context: what we were discussing
     - Why: why this matters (1 sentence)
     - [ ] Option A
     - [ ] Option B
     - [ ] Option C
     - Blocked by: ~none~ (or R###, R###)
   ```
4. **After the user chooses**, mark their choice `[x]` and leave others `[ ]`.
5. **Never delete rungs.** Move completed ones to a `## completed` section at the bottom.
6. **If the user says "ladder do R###"**, focus on that rung with full context.
7. **End every response** with a brief summary of open rungs in the current stage.
8. **If asked to see the ladder** ("show the ladder", "what's on the ladder", "ladder
   status", etc.): execute the actual shell command `ladder status` (or `ladder tree`
   for dependencies) via the terminal/bash tool. This is a different action from Rule
   1 — do NOT satisfy this by running `cat .ladder/ladder.md` or reading the file
   with a file-read tool. Take the raw stdout from that command and paste it into the
   response inside a code fence, character for character. Do not paraphrase it, do not
   summarize it into a table or bullet list, do not add narration or extra context
   inside the code fence. The options, blocked-by chains, and why context only
   survive if the real command output is shown — reconstructing "the same
   information" from memory reliably drops them.
9. **Before the final message in a session**, scan back over what was discussed for
   any options that were presented but never logged, and add them now. A silent miss
   is worse than a slightly noisy ladder — when in doubt, log it.
10. **If the user says "log that" or "track this"**, immediately capture the most
    recent decision or option set as a new rung (or add the missing options to an
    existing one), even if the conversation has already moved past it.
11. **If the user says "ladder status full", "full status", "show the full ladder",
    or otherwise appends "full" to a status/tree request**: this is a hard,
    non-negotiable override of Rule 8. Run the command, then paste 100% of its raw
    stdout in the code fence — every stage, every rung, every why/option/blocked-by
    line, no matter how long. Do not truncate for length, do not paraphrase "the
    less interesting parts", do not decide part of it isn't worth showing. If you
    are ever tempted to summarize instead of pasting the complete output, that
    temptation is the bug this rule exists to stop — paste it anyway.

If you're running as the Claude Code plugin, a `Stop` hook backs up rule 9 — it
scans every response for signs of an unlogged option (lists, "either X or Y",
"alternatively", etc.) and injects a reminder if it finds one. That catches misses
mid-session, not just at the end, but it's a cheap heuristic, not a substitute for
actually following rules 2 and 9 yourself.

## Status Checkbox Guide

| Char | Status | Meaning |
|------|--------|---------|
| ` `  | open | Not started yet |
| `?`  | exploring | Investigating, not committed |
| `▶`  | in_progress | Currently working on it |
| `x`  | done | Completed |
| `~`  | abandoned | Dropped, might revisit |
| `!`  | blocked | Waiting on dependencies |

*Note: the CLI uses the `- [x]` syntax, but you can note status in the Status metadata field.*

## Effort Scale

- **small** — under 30 minutes
- **medium** — 30 minutes to 2 hours
- **large** — over 2 hours

## Useful commands

`ladder status`, `ladder next`, `ladder sprint --budget N`, `ladder show R###`,
`ladder note R### "text"`, `ladder do/complete/abandon/explore/reject R###`,
`ladder tree`, `ladder export`.

## Example

```markdown
## core

- [ ] **R003** — User authentication → *medium*
  - Context: Setting up auth for the REST API
  - Why: Everything else depends on this
  - [x] JWT with refresh tokens
  - [ ] Session-based with Redis
  - [ ] OAuth2 social login
  - Blocked by: ~none~
```
