from unittest.mock import patch
from pathlib import Path
import pytest

from codexor.repo import _ensure_git_repo, ensure_clean_worktree, resolve_repo_target
from codexor.errors import ValidationError, DirtyWorktreeError


@patch("codexor.repo.run_command")
def test_ensure_git_repo_success(mock_run):
    mock_run.return_value = "true\n"
    _ensure_git_repo(Path("."))
    mock_run.assert_called_once_with(["git", "rev-parse", "--is-inside-work-tree"], cwd=Path("."))


@patch("codexor.repo.run_command")
def test_ensure_git_repo_failure(mock_run):
    mock_run.return_value = "false\n"
    with pytest.raises(ValidationError):
        _ensure_git_repo(Path("."))


@patch("codexor.repo.run_command")
@patch("codexor.repo._ensure_git_repo")
def test_ensure_clean_worktree_success(mock_ensure, mock_run):
    mock_run.return_value = ""
    ensure_clean_worktree(Path("."))
    mock_run.assert_called_once_with(["git", "status", "--porcelain"], cwd=Path("."))


@patch("codexor.repo.run_command")
@patch("codexor.repo._ensure_git_repo")
def test_ensure_clean_worktree_dirty(mock_ensure, mock_run):
    mock_run.return_value = " M file.py\n"
    with pytest.raises(DirtyWorktreeError):
        ensure_clean_worktree(Path("."))


@patch("codexor.repo.resolve_repo_full_name")
@patch("codexor.repo.ensure_clean_worktree")
def test_resolve_repo_target(mock_ensure, mock_resolve_name, tmp_path):
    mock_resolve_name.return_value = "owner/repo"
    
    resolved = resolve_repo_target(tmp_path)
    
    assert resolved.repo_full_name == "owner/repo"
    assert resolved.local_path == tmp_path
    assert not resolved.is_temporary_clone
    assert not resolved.cleanup_on_success
    mock_ensure.assert_called_once_with(tmp_path)
