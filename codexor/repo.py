"""Repository resolution and local workspace policies."""

from __future__ import annotations

from pathlib import Path

from .command import run_command
from .errors import DirtyWorktreeError, ValidationError
from .github import resolve_repo_full_name
from .models import ResolvedRepo


def _ensure_git_repo(path: Path) -> None:
    output = run_command(["git", "rev-parse", "--is-inside-work-tree"], cwd=path).strip()
    if output.lower() != "true":
        raise ValidationError(f"Path is not a git repository: {path}")


def ensure_clean_worktree(path: Path) -> None:
    """Fail fast when repository has local modifications."""
    _ensure_git_repo(path)
    status = run_command(["git", "status", "--porcelain"], cwd=path).strip()
    if status:
        raise DirtyWorktreeError(
            "Local repository has uncommitted changes. codexor requires a clean worktree."
        )


def resolve_repo_target(cwd: Path) -> ResolvedRepo:
    """Resolve current local path into a concrete working repository."""
    if not cwd.exists() or not cwd.is_dir():
        raise ValidationError(f"Local repository path does not exist: {cwd}")

    ensure_clean_worktree(cwd)
    repo_full_name = resolve_repo_full_name(cwd)
    if not repo_full_name:
        raise ValidationError(f"Could not resolve GitHub repo name from local path: {cwd}")

    return ResolvedRepo(
        repo_full_name=repo_full_name,
        local_path=cwd,
        is_temporary_clone=False,
        cleanup_on_success=False,
    )
