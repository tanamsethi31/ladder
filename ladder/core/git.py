"""Git integration for auto-committing ladder changes."""

from __future__ import annotations

import os
from pathlib import Path

try:
    import git

    HAS_GIT = True
except ImportError:
    HAS_GIT = False


def auto_commit(ladder_path: Path, message: str | None = None) -> bool:
    """Auto-commit ladder.md changes if inside a git repo."""
    if not HAS_GIT:
        return False

    try:
        repo = git.Repo(ladder_path.parent, search_parent_directories=True)
        # is_dirty(path=...) matches against the path relative to the repo root,
        # not just the filename — ladder.md always lives nested under .ladder/,
        # so filtering by ladder_path.name alone never matched and this silently
        # never committed anything.
        rel_path = os.path.relpath(ladder_path.resolve(), repo.working_tree_dir)
        if repo.is_dirty(path=rel_path, untracked_files=True):
            repo.git.add(str(ladder_path))
            msg = message or "Update ladder"
            repo.index.commit(msg)
            return True
    except (git.InvalidGitRepositoryError, git.GitCommandError, git.NoSuchPathError):
        pass

    return False
