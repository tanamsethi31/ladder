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

- [x] **R018** — demo.gif is stale against the new brand colors → *medium*
  - Why: assets/demo.gif still shows the old GitHub-blue palette; needs re-recording, not just a color swap
  - Note: Regenerated with vhs (charmbracelet), scripted this time via a committed assets/demo.tape (the original wasn't committed, so it wasn't reproducible). Fully CLI-driven -- init, abandon the generic placeholder, two adds building a real blocked-by chain, status, next -- no manual markdown injection, so anyone with vhs + ladder installed can regenerate it verbatim. Custom VHS theme JSON matches the actual brand palette (LADDER_THEME/HTML CSS vars) instead of a generic terminal theme. 18.8s, 615KB, close to the original's footprint.

- [x] **R019** — Enforce status-relay via UserPromptSubmit+Stop hook block → *large*
  - Why: Rule 11 (hard, non-negotiable, paste 100%) was violated on the very first real dogfood test - I paraphrased instead of pasting, twice. Prompt wording alone is proven unreliable; needed actual enforcement that blocks the turn until the real output is verifiably present

- [x] **R020** — Stop hook false-positive: bare lists triggered constantly → *small*
  - Why: Structural '2+ list items' check fired on nearly every multi-point response (status recaps, step lists) regardless of content; removed it, kept only explicit choice-language patterns

- [x] **R021** — Ambiguous pronoun references to rungs are unreliable → *medium*
  - Why: Discovered via R008's A/B test: 'why is that still undecided' with multiple candidate rungs failed in both terse (derailed into logging talk, never answered) and full (confidently named the wrong rung) conditions. Not a terse-vs-full issue - a real, separate gap in resolving vague references when several rungs could match.
  - Note: Added Rule 12 (both system.md and SKILL.md, kept in sync): on a vague/pronoun reference that could match 2+ open or exploring rungs, run status/tree first, then either name the one specific rung you're confident matches or ask which one -- don't guess, don't drift into a different topic. Verified live with a real A/B, same method as R008 (--plugin-dir against this repo, one variable changed): fixture with 2 genuinely ambiguous candidates (R010 exploring, R011 open, both undecided), prompt 'why is that still undecided'. Baseline (git-stashed back to pre-rule-12): silently picked R010, never mentioned R011 existed, answered as if settled -- reproduces the original failure exactly. Fixed: named both candidates with their real details and asked which one. Also checked the fix doesn't over-trigger -- a 3rd fixture with only one genuinely undecided rung (the other already done) got a direct answer, no unnecessary clarifying question.

- [x] **R022** — system.md (universal prompt) was stale vs SKILL.md → *medium*
  - Why: Missing rule 11 entirely (the hard 'full' override) and the Useful commands section - anyone using ladder via Cursor/Copilot/ChatGPT copy-paste had strictly weaker protection against the exact paraphrasing failure I hit myself, with zero hook backup to compensate since that's Claude-Code-specific
  - Note: Verified fixed via 3 live tests using Claude with --append-system-prompt only (no --plugin-dir, no hooks, no skill auto-load) - simulates exactly what a Cursor/Copilot/ChatGPT user experiences. Rule 8 (real status output): pass. Rule 2 (log a plain-language decision): pass, verified the actual file content + ladder validate, not just the claimed response. Rule 11 (full override, zero hook backup): pass, complete correct output. The universal prompt-only mechanism genuinely works once the prompt itself is kept in sync.

- [x] **R023** — auto_commit never actually committed anything → *medium*
  - Why: Two real bugs: is_dirty() defaults to ignoring untracked files (first-ever commit silently never happened), and filtered by ladder_path.name instead of path-relative-to-repo-root (never matched .ladder/ladder.md, the only real layout). This is a core advertised feature - README says 'Auto-commits - optionally commits ladder changes to git' - that may have never worked in any real usage.
  - Note: Fixed both: added untracked_files=True to is_dirty(), and filter by path relative to repo root (os.path.relpath against repo.working_tree_dir) instead of ladder_path.name. Verified with real git repos (no mocking): first-commit-of-untracked-nested-file now correctly commits, no-changes correctly stays a no-op (no empty commits), modified-tracked-file still commits. Confirmed the new tests actually catch the bug - 4/6 fail against the pre-fix code when stashed. git.py coverage 60% -> 91%.

- [x] **R024** — Hardening pass: models.py tests + dead code + misleading docstring → *medium*
  - Why: get_stage_for_rung was defined but never called anywhere - deleted. is_unblocked()'s docstring claimed it checks if blockers are done, but it only checks blocker-ID existence; the real done-check lives separately in get_unblocked_rungs. Fixed the docstring to be honest rather than refactor working, tested logic. models.py and parser.py now both 100% covered, git.py 91%.

- [x] **R025** — Hardening: renderer.py pure functions + validate command's other rules → *medium*
  - Why: renderer.py's status/style mapping functions and cli.py's validate command had 4 of 5 error types and all 3 warning types completely untested - only the broken-blocker error had coverage. Also caught my own test-writing bug: ABANDONED counts as done, so [DONE, ABANDONED] is fully complete, not the any-done-no-progress case I assumed.

- [x] **R026** — Hardening: cli.py next/prompt/_priority_sort_key + git.py auto_commit tests → *medium*
  - Context: Continuation of the systematic coverage-gap hardening pass across the core module
  - Why: Closed the remaining untested branches so cli.py is fully exercised, not just its happy paths
  - Note: Covered: next() empty-unblocked branch + waiting-on-dependencies listing, next() stage-progression nudge, prompt command (happy path + missing-file fallback), abandon, all single-rung not-found paths (show/do/complete/abandon/explore/reject), no-ladder error message, init-twice no-overwrite, add's new-stage/blocker-warning/parent-warning/blocked-by-line branches, and _priority_sort_key's for-else fallback when a rung isn't in any stage. cli.py coverage 79%->99% (only the __main__ guard left, not worth testing). Full suite: 108 passed, ruff/mypy clean.

- [x] **R027** — Harden renderer.py to 100% + fix real [x]-checkbox-swallowed-by-markup bug in render_rung → *medium*
  - Context: Continuation of the coverage-gap hardening pass, this time targeting renderer.py's render_status/render_tree/render_rung/render_next_suggestions/render_validation/render_html functions directly
  - Why: Direct unit tests with full-attribute fixtures caught a genuine terminal-output bug that CLI-level tests never exercised
  - Note: Also found and fixed the same markup-swallowing bug in 3 more places: render_tree (title/why/options/project/stage-name via Tree.add), render_rung's info table (context/why/parent/blocked_by/note via Table.add_row), and 7 confirmation-echo call sites in cli.py (add/do/complete/note/abandon/explore/reject all interpolate free text into a markup-enabled console.print). Root cause: Rich parses plain strings as markup in console.print, Tree.add, and Table cells alike, so any '[...]' in an AI-written title/why/note was being silently swallowed, not just the [x]/[  ] checkbox glyphs. Fixed via Text()-wrapping (render_rung) and rich.markup.escape() (render_tree, cli.py confirmations) at every site free text reaches a markup-parsing call. Confirmed against real terminal output, not just recorded console. renderer.py + cli.py both at 100%/99%. 125 tests passed.

- [x] **R029** — Harden git.py to 100%: cover the ImportError fallback branch → *small*
  - Context: Closing the last coverage gap in the core module set
  - Why: gitpython is a hard pip dependency, but it still raises ImportError at import time if the git binary itself is missing from PATH (e.g. a stripped container) -- worth actually testing, not just assuming
  - Note: git.py 91%->100%. Simulated the ImportError branch for real by blanking sys.modules['git'] and importlib.reload()-ing the module so the top-level try/except actually re-runs, rather than just monkeypatching the HAS_GIT flag after the fact (that only covers auto_commit's runtime check, not the import-time branch itself). Restores real state in a finally block. All core modules (models/parser/renderer/git) now 100%, cli.py 99% (only __main__ guard left). Also cleaned up two bookkeeping slips from the R027 batch: a stray test rung (R028) that leaked into the real ladder.md from a non-isolated manual verification run, and R027 itself never actually being marked done despite being finished.
