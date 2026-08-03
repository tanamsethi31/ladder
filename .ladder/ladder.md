---
project: ladder
version: 1
---

## foundation

- [~] **R001** — Project scaffold & folder structure → *small*
  - Context: Setting up the repo
  - Why: Everything builds on this
  - Note: Abandoned: init placeholder
  - Status: abandoned

## core

- [~] **R002** — Your first real feature → *medium*
  - Context: What you are building right now
  - Why: The meat of the project
  - Note: Abandoned: init placeholder
  - Status: abandoned

## expansion

- [x] **R003** — HTML export → *medium*
  - Why: Static HTML render of the ladder for sharing outside the terminal

- [x] **R004** — Better AI-formatting tolerance in the parser → *medium*
  - Why: Different AI assistants drift from the exact markdown format over long sessions

- [x] **R005** — Stage auto-progression suggestions → *small*
  - Why: Nudge which stage to focus on next based on completion state

- [x] **R006** — note command → *small*
  - Why: Attach free-text notes to rungs without changing status

- [x] **R007** — sprint command → *medium*
  - Why: Budget-based picker for planning a batch of work

## plugin

- [?] **R008** — Hook verbosity: terse pointer vs full status render → *small*
  - Why: Went with terse counts+pointer for now to save context tokens every session; revisit if that reads worse in practice than always showing full ladder status
  - Status: exploring

- [x] **R009** — Claude Code plugin: hook + skill → *large*
  - Why: Wire ladder into the agent loop instead of manual copy-paste system prompt

- [x] **R010** — Stop hook: catch unlogged options mid-session → *medium*
  - Why: Rule 9 only self-checked once at session end; a deterministic Stop hook now nudges after every turn instead
