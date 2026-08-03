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

- [x] **R008** — Hook verbosity: terse pointer vs full status render → *small*
  - Why: Terse status line + skill pointer at SessionStart, not the full `ladder status` render. Settled by a 12-trial controlled A/B test (3 scenarios x terse/full x 2 reps, same fixture, only the injected context varied): terse showed no behavioral deficit and no round-trip penalty on the scenarios designed to expose one (blocked-dependency, "what's next" — 2/2 pass both conditions; turn counts 5.0 terse vs 4.83 full). Terse's real, measured token savings (250-800+ tok/session, scaling with project size) stand uncontested.
  - Note: Method, for reproducing or extending this test — two `--plugin-dir` variants (real repo vs a temp copy with session_start.py patched to inject full status), same fixture ladder (a blocked-dependency chain, a multi-stage "what's next" setup, one distinctive exploring rung), graded against real CLI output as ground truth. The one scenario both conditions struggled with (ambiguous pronoun reference) failed differently per condition, meaning it wasn't actually a terse-vs-full effect — spun out as R021 rather than counted as evidence either way.

- [x] **R009** — Claude Code plugin: hook + skill → *large*
  - Why: Wire ladder into the agent loop instead of manual copy-paste system prompt

- [x] **R010** — Stop hook: catch unlogged options mid-session → *medium*
  - Why: Rule 9 only self-checked once at session end; a deterministic Stop hook now nudges after every turn instead

- [x] **R011** — Explicit 'full' override for status/tree → *small*
  - Why: Rule 8 alone had already been rewritten 3x historically and still risked paraphrasing; an explicit non-negotiable trigger phrase is cheaper to try before building transcript-verification enforcement

- [x] **R012** — Strip ANSI from chat-relayed CLI output → *small*
  - Why: Raw stdout can contain literal ANSI escape bytes (confirmed live, FORCE_COLOR-forced) that would show as garbled text if pasted into a chat code fence

- [x] **R013** — Rule 7 summary must always follow rule 11 full dump → *small*
  - Why: Live test showed the trailing open-rungs summary was inconsistently included after a full status dump

- [▶] **R014** — Subtle/prose-only option capture → *large*
  - Why: Both Claude's own judgment and the Stop-hook regex heuristic only catch list-formatted or trigger-phrase options; a recommendation woven into plain prose (no list, no 'either/or') likely still slips through both layers
  - Note: Part 1 shipped: 'ladder scan <text>' is now a real CLI command (ladder/core/checks.py + cli.py), provider-agnostic and reusable by any tool's hook system, not just Claude Code. The plugin's stop_check.py now delegates to it via subprocess instead of duplicating the regex - single source of truth. Part 2 (the actual LLM semantic layer, type:'prompt' Stop hook) still pending.
  - Status: in_progress

- [x] **R015** — HTML export design pass → *medium*
  - Why: Weakest of the three output surfaces per user feedback; brought it up to the level of the terminal/plugin work

- [x] **R016** — Terminal output consistency pass → *small*
  - Why: Rung tables auto-sized per-stage, causing ragged column widths across a status view; tree view was also missing brand emoji + stage-completion color that status already had

- [x] **R017** — Brand color identity across CLI/HTML/README → *medium*
  - Why: Every color was a literal copy of GitHub's Primer palette; replaced with a warm amber/wood identity tied to the ladder theme, applied via a Rich Theme (terminal), CSS variables (HTML export), and shields.io badge colors (README)

- [ ] **R018** — demo.gif is stale against the new brand colors → *medium*
  - Why: assets/demo.gif still shows the old GitHub-blue palette; needs re-recording, not just a color swap

- [x] **R019** — Enforce status-relay via UserPromptSubmit+Stop hook block → *large*
  - Why: Rule 11 (hard, non-negotiable, paste 100%) was violated on the very first real dogfood test - I paraphrased instead of pasting, twice. Prompt wording alone is proven unreliable; needed actual enforcement that blocks the turn until the real output is verifiably present

- [x] **R020** — Stop hook false-positive: bare lists triggered constantly → *small*
  - Why: Structural '2+ list items' check fired on nearly every multi-point response (status recaps, step lists) regardless of content; removed it, kept only explicit choice-language patterns

- [?] **R021** — Ambiguous pronoun references to rungs are unreliable → *medium*
  - Why: Discovered via R008's A/B test: 'why is that still undecided' with multiple candidate rungs failed in both terse (derailed into logging talk, never answered) and full (confidently named the wrong rung) conditions. Not a terse-vs-full issue - a real, separate gap in resolving vague references when several rungs could match.
  - Status: exploring
