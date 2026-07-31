# 🪜 Ladder

> Track every branch, stage, and alternative path in your AI pair-programming sessions.

When pair-programming with AI, every decision presents multiple paths. You pick one. The others vanish into scrollback. Three hours later, you realize you needed that other path too.

**Ladder captures every branch, stages them by effort, and lets you climb back to any rung.**

## Install

```bash
pip install ladder-cli
```

## Quick Start

```bash
# 1. Initialize a ladder in your project
cd my-project
ladder init --project "My API"

# 2. Paste the system prompt into your AI assistant
ladder prompt

# 3. Start building — the AI populates the ladder automatically

# 4. Check your progress anytime
ladder status
```

## How It Works

Ladder uses a **Markdown + YAML** file (`.ladder/ladder.md`) that both you and your AI can read and write:

```markdown
---
project: My API
version: 1
---

## foundation

- [x] **R001** — Project scaffold → *small*
  - Context: Setting up the repo
  - Why: Everything builds on this

## core

- [ ] **R003** — User authentication → *medium*
  - Context: REST API auth
  - Why: Everything else depends on this
  - [x] JWT with refresh tokens
  - [ ] Session-based with Redis
  - [ ] OAuth2 social login
  - Blocked by: ~none~
```

**Why this format wins:**
- ✅ **Git-friendly** — clean diffs, full history
- ✅ **AI-friendly** — any LLM reads/writes markdown natively
- ✅ **Human-friendly** — open in any editor, understand in 30 seconds
- ✅ **CLI-friendly** — trivial to parse and render

## Commands

| Command | Description |
|---------|-------------|
| `ladder init` | Create a new ladder in the current directory |
| `ladder status` | Show the full project ladder |
| `ladder show R003` | Detailed info for a specific rung |
| `ladder do R003` | Mark a rung as in-progress |
| `ladder complete R003` | Mark a rung as done |
| `ladder abandon R003 --reason "deprecated"` | Mark a rung as abandoned |
| `ladder tree` | Show dependencies as an ASCII tree |
| `ladder prompt` | Print the system prompt for your AI |

## Why Ladder?

- **Works with any AI** — Claude, GPT-4, Cursor, Copilot, whatever
- **No lock-in** — your data is plain Markdown in your repo
- **Auto-commits** — optionally commits ladder changes to git
- **Dependency aware** — knows when a rung is blocked by another
- **Effort-weighted** — small/medium/large so you can plan sprints

## Contributing

1. Fork the repo
2. `pip install -e ".[dev]"`
3. `pytest`
4. Open a PR

## License

MIT
