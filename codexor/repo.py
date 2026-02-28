"""Repository resolution and local workspace policies."""

from __future__ import annotations

import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

from .command import run_command
from .errors import DirtyWorktreeError, ValidationError
from .github import resolve_repo_full_name
from .models import ResolvedRepo

REMOTE_REPO_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


def _is_remote_repo_target(repo_arg: str) -> bool:
    candidate = repo_arg.strip()
    if Path(candidate).exists():
        return False
    return bool(REMOTE_REPO_PATTERN.fullmatch(candidate))


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


def _clone_remote_repo(repo_full_name: str) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    workspace_root = Path.home() / ".codexor" / "workspaces"
    workspace_root.mkdir(parents=True, exist_ok=True)
    owner, repo = repo_full_name.split("/", maxsplit=1)
    clone_path = workspace_root / f"{owner}__{repo}__{stamp}"
    run_command(["git", "clone", f"https://github.com/{repo_full_name}.git", str(clone_path)])
    return clone_path


def resolve_repo_target(repo_arg: str) -> ResolvedRepo:
    """Resolve local path or owner/repo into a concrete working repository."""
    candidate = repo_arg.strip()
    if not candidate:
        raise ValidationError("--repo must not be empty.")

    if _is_remote_repo_target(candidate):
        local_path = _clone_remote_repo(candidate)
        ensure_clean_worktree(local_path)
        return ResolvedRepo(
            repo_full_name=candidate,
            local_path=local_path,
            is_temporary_clone=True,
            cleanup_on_success=True,
        )

    local_path = Path(candidate).expanduser().resolve()
    if not local_path.exists() or not local_path.is_dir():
        raise ValidationError(f"Local repository path does not exist: {local_path}")

    ensure_clean_worktree(local_path)
    repo_full_name = resolve_repo_full_name(local_path)
    if not repo_full_name:
        raise ValidationError(f"Could not resolve GitHub repo name from local path: {local_path}")

    return ResolvedRepo(
        repo_full_name=repo_full_name,
        local_path=local_path,
        is_temporary_clone=False,
        cleanup_on_success=False,
    )


def cleanup_temporary_repo(path: Path) -> None:
    """Remove temporary clone directory."""
    if path.exists():
        shutil.rmtree(path, ignore_errors=True)
