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

- [x] **R014** — Subtle/prose-only option capture → *large*
  - Why: Both Claude's own judgment and the Stop-hook regex heuristic only catch list-formatted or trigger-phrase options; a recommendation woven into plain prose (no list, no 'either/or') likely still slips through both layers
  - Note: Part 2 shipped: type:'prompt' Stop hook (Haiku, verified {ok,reason} contract via the hooks guide) added alongside the existing regex/ladder-scan first-pass. Live-tested: correctly flagged a genuinely prose-only recommendation (no list, no either/or - the exact case R014 was created for) and the model explicitly referenced 'the hook's suggestion' in its response. Clean on a trivial response (2+2). One oddity noted, not a functional bug: in an empty-directory/no-ladder edge case, the response text itself narrated the hook's internal {ok:true} JSON rather than just answering cleanly - likely a prompt-phrasing artifact from an unusually-constrained test question in a contrived empty dir, not a real false-positive (no spurious block/nudge occurred). Worth another look if it recurs in real dogfooding.

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

- [x] **R022** — system.md (universal prompt) was stale vs SKILL.md → *medium*
  - Why: Missing rule 11 entirely (the hard 'full' override) and the Useful commands section - anyone using ladder via Cursor/Copilot/ChatGPT copy-paste had strictly weaker protection against the exact paraphrasing failure I hit myself, with zero hook backup to compensate since that's Claude-Code-specific
  - Note: Verified fixed via 3 live tests using Claude with --append-system-prompt only (no --plugin-dir, no hooks, no skill auto-load) - simulates exactly what a Cursor/Copilot/ChatGPT user experiences. Rule 8 (real status output): pass. Rule 2 (log a plain-language decision): pass, verified the actual file content + ladder validate, not just the claimed response. Rule 11 (full override, zero hook backup): pass, complete correct output. The universal prompt-only mechanism genuinely works once the prompt itself is kept in sync.

- [x] **R023** — auto_commit never actually committed anything → *medium*
  - Why: Two real bugs: is_dirty() defaults to ignoring untracked files (first-ever commit silently never happened), and filtered by ladder_path.name instead of path-relative-to-repo-root (never matched .ladder/ladder.md, the only real layout). This is a core advertised feature - README says 'Auto-commits - optionally commits ladder changes to git' - that may have never worked in any real usage.
  - Note: Fixed both: added untracked_files=True to is_dirty(), and filter by path relative to repo root (os.path.relpath against repo.working_tree_dir) instead of ladder_path.name. Verified with real git repos (no mocking): first-commit-of-untracked-nested-file now correctly commits, no-changes correctly stays a no-op (no empty commits), modified-tracked-file still commits. Confirmed the new tests actually catch the bug - 4/6 fail against the pre-fix code when stashed. git.py coverage 60% -> 91%.

- [x] **R024** — Hardening pass: models.py tests + dead code + misleading docstring → *medium*
  - Why: get_stage_for_rung was defined but never called anywhere - deleted. is_unblocked()'s docstring claimed it checks if blockers are done, but it only checks blocker-ID existence; the real done-check lives separately in get_unblocked_rungs. Fixed the docstring to be honest rather than refactor working, tested logic. models.py and parser.py now both 100% covered, git.py 91%.

- [ ] **R025** — Hardening: renderer.py pure functions + validate command's other rules → *medium*
  - Why: renderer.py's status/style mapping functions and cli.py's validate command had 4 of 5 error types and all 3 warning types completely untested - only the broken-blocker error had coverage. Also caught my own test-writing bug: ABANDONED counts as done, so [DONE, ABANDONED] is fully complete, not the any-done-no-progress case I assumed.
