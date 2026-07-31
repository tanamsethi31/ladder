"""Git integration for auto-committing ladder changes."""

from __future__ import annotations

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
        if repo.is_dirty(path=ladder_path.name):
            repo.git.add(str(ladder_path))
            msg = message or "Update ladder"
            repo.index.commit(msg)
            return True
    except (git.InvalidGitRepositoryError, git.GitCommandError, git.NoSuchPathError):
        pass

    return False
