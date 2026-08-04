"""Tests for auto_commit — real git repos, no mocking, matching the project's
existing testing style. Covers two real bugs found by hand: is_dirty() ignoring
untracked files by default (so the very first commit silently never happened),
and filtering by ladder_path.name instead of the path relative to repo root (so
it never matched .ladder/ladder.md, which is the only way this file is ever
actually laid out)."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import git as gitpython
import pytest

import ladder.core.git as git_module
from ladder.core.git import auto_commit


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> gitpython.Repo:
    monkeypatch.chdir(tmp_path)
    r = gitpython.Repo.init(tmp_path)
    with r.config_writer() as cfg:
        cfg.set_value("user", "name", "Test")
        cfg.set_value("user", "email", "test@test.com")
    return r


def test_first_commit_of_a_new_nested_file(repo: gitpython.Repo, tmp_path: Path) -> None:
    ladder_file = tmp_path / ".ladder" / "ladder.md"
    ladder_file.parent.mkdir()
    ladder_file.write_text("---\nproject: test\n---\n")

    assert auto_commit(ladder_file, "first commit") is True
    assert not repo.is_dirty(untracked_files=True)
    assert repo.head.commit.message == "first commit"


def test_no_changes_does_not_commit(repo: gitpython.Repo, tmp_path: Path) -> None:
    ladder_file = tmp_path / ".ladder" / "ladder.md"
    ladder_file.parent.mkdir()
    ladder_file.write_text("content")
    auto_commit(ladder_file, "first commit")

    assert auto_commit(ladder_file, "should not happen") is False
    assert repo.head.commit.message == "first commit"


def test_second_commit_of_a_modified_tracked_file(repo: gitpython.Repo, tmp_path: Path) -> None:
    ladder_file = tmp_path / ".ladder" / "ladder.md"
    ladder_file.parent.mkdir()
    ladder_file.write_text("v1")
    auto_commit(ladder_file, "first commit")

    ladder_file.write_text("v2")
    assert auto_commit(ladder_file, "second commit") is True
    assert repo.head.commit.message == "second commit"


def test_default_message_when_none_given(repo: gitpython.Repo, tmp_path: Path) -> None:
    ladder_file = tmp_path / ".ladder" / "ladder.md"
    ladder_file.parent.mkdir()
    ladder_file.write_text("content")

    assert auto_commit(ladder_file) is True
    assert repo.head.commit.message == "Update ladder"


def test_no_git_repo_returns_false_no_exception(tmp_path: Path) -> None:
    ladder_file = tmp_path / ".ladder" / "ladder.md"
    ladder_file.parent.mkdir()
    ladder_file.write_text("content")

    assert auto_commit(ladder_file, "test") is False


def test_has_git_false_returns_false_immediately(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(git_module, "HAS_GIT", False)
    ladder_file = tmp_path / ".ladder" / "ladder.md"
    ladder_file.parent.mkdir()
    ladder_file.write_text("content")

    assert auto_commit(ladder_file, "test") is False


def test_import_error_sets_has_git_false(monkeypatch: pytest.MonkeyPatch) -> None:
    """gitpython is a hard pip dependency, but GitPython itself raises
    ImportError at import time if the `git` executable isn't on PATH (package
    installed fine, binary missing — e.g. a stripped-down container). Forces
    that by blanking sys.modules["git"] and reloading, so the module's
    top-level try/except actually re-runs instead of just flipping the flag."""
    monkeypatch.setitem(sys.modules, "git", None)
    try:
        importlib.reload(git_module)
        assert git_module.HAS_GIT is False
    finally:
        monkeypatch.undo()
        importlib.reload(git_module)
        assert git_module.HAS_GIT is True
