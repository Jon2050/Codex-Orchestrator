"""Markdown report writer for codexor runs."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from .models import RunReport


def _sanitize_for_path(value: str) -> str:
    normalized = "".join(char if char.isalnum() else "-" for char in value.lower())
    cleaned = "-".join(segment for segment in normalized.split("-") if segment)
    return cleaned or "run"


def build_report_path(repo_full_name: str, milestone: str) -> Path:
    """Create deterministic run report path under user home."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    repo_slug = _sanitize_for_path(repo_full_name.replace("/", "-"))
    milestone_slug = _sanitize_for_path(milestone)
    report_dir = Path.home() / ".codexor" / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    return report_dir / f"{repo_slug}__{milestone_slug}__{stamp}.md"


def _format_dt(value: datetime | None) -> str:
    if value is None:
        return "-"
    return value.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def render_report_markdown(report: RunReport) -> str:
    """Render report model into markdown output."""
    lines: list[str] = []
    
    run_id = report.started_at.astimezone(timezone.utc).strftime("%Y%m%d-%H%M%S")
    
    duration_str = "-"
    if report.finished_at:
        duration_sec = int((report.finished_at - report.started_at).total_seconds())
        duration_str = f"{duration_sec}s"

    lines.append(f"# codexor run report: {report.repo_full_name} / {report.milestone}")
    lines.append("")
    lines.append("## Run Summary")
    lines.append("")
    lines.append(f"- Run ID: `{run_id}`")
    lines.append(f"- Repository: `{report.repo_full_name}`")
    lines.append(f"- Milestone: `{report.milestone}`")
    lines.append(f"- Started: `{_format_dt(report.started_at)}`")
    lines.append(f"- Finished: `{_format_dt(report.finished_at)}`")
    lines.append(f"- Duration: `{duration_str}`")
    lines.append(f"- Status: `{report.status.value if report.status else 'running'}`")
    lines.append("")
    lines.append("## Issue Results")
    lines.append("")
    lines.append("| Issue Key | Number | Title | Start | End | Duration (s) | Status | Signal | Notes |")
    lines.append("|---|---:|---|---|---|---:|---|---|---|")

    for entry in report.entries:
        issue_key = entry.issue.key.raw if entry.issue.key else "-"
        problem = entry.note.replace("|", "/")
        title = entry.issue.title.replace("|", "/")
        lines.append(
            "| {issue_key} | #{number} | {title} | {start} | {end} | {duration} | {status} | {signal} | {note} |".format(
                issue_key=issue_key,
                number=entry.issue.number,
                title=title,
                start=_format_dt(entry.started_at),
                end=_format_dt(entry.finished_at),
                duration=entry.duration_seconds,
                status=entry.status.value,
                signal=entry.signal.value if entry.signal else "-",
                note=problem if problem else "-",
            )
        )
    lines.append("")
    return "\n".join(lines)


class ReportWriter:
    """Writes one markdown report file for each run."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def write(self, report: RunReport) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(render_report_markdown(report), encoding="utf-8")
