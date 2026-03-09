"""Core dataclasses and enums."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path


class FinalSignal(str, Enum):
    """Codex handshake signal values."""

    ALL_DONE = "ALL DONE"
    BREAK_ON_ERROR = "BREAK ON ERROR"
    INVALID = "INVALID"


class IssueStatus(str, Enum):
    """Per-issue run status for reporting."""

    DONE = "done"
    BLOCKED = "blocked"
    HALTED = "halted"


class RunStatus(str, Enum):
    """Overall run status."""

    COMPLETED = "completed"
    HALTED = "halted"
    BLOCKED = "blocked"
    FAILED_CONFIG = "failed_config"
    FAILED_DEPENDENCY = "failed_dependency"
    INTERRUPTED = "interrupted"


@dataclass(slots=True, frozen=True)
class RunConfig:
    """Run command configuration."""

    cwd: Path
    milestone: str
    prompt_template: Path
    cli_tool: str = "codex"


@dataclass(slots=True, frozen=True)
class IssueKey:
    """Parsed issue key from issue title."""

    raw: str
    major: int
    minor: str

    @property
    def sort_tuple(self) -> tuple[int, tuple[int, ...]]:
        return (self.major, tuple(int(char) for char in self.minor))


@dataclass(slots=True)
class MilestoneIssue:
    """Issue metadata used by the run controller."""

    number: int
    title: str
    body: str
    url: str
    key: IssueKey | None = None


@dataclass(slots=True, frozen=True)
class ResolvedRepo:
    """Resolved repository context for the run."""

    repo_full_name: str
    local_path: Path
    is_temporary_clone: bool
    cleanup_on_success: bool


@dataclass(slots=True, frozen=True)
class CodexRunResult:
    """Result from one Codex process execution."""

    exit_code: int
    last_non_empty_line: str
    output_tail: str


@dataclass(slots=True)
class IssueRunResult:
    """Result for one issue execution."""

    issue: MilestoneIssue
    started_at: datetime
    finished_at: datetime
    duration_seconds: int
    status: IssueStatus
    signal: FinalSignal
    note: str


@dataclass(slots=True)
class RunReport:
    """Aggregate report for one full run."""

    repo_full_name: str
    milestone: str
    started_at: datetime
    finished_at: datetime | None = None
    status: RunStatus | None = None
    entries: list[IssueRunResult] = field(default_factory=list)
