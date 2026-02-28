"""Run controller and state machine."""

from __future__ import annotations

from datetime import datetime, timezone

from .codex_runner import CodexRunner
from .errors import ValidationError
from .github import load_open_milestone_issues
from .issue_key import attach_and_sort_issues
from .models import (
    FinalSignal,
    IssueRunResult,
    IssueStatus,
    RunConfig,
    RunReport,
    RunStatus,
)
from .reporting import ReportWriter, build_report_path
from .repo import cleanup_temporary_repo, resolve_repo_target
from .signals import parse_final_signal
from .template import load_prompt_template, render_prompt


class Orchestrator:
    """Coordinates end-to-end milestone issue execution."""

    def __init__(self, config: RunConfig) -> None:
        self.config = config
        self.codex_runner = CodexRunner()

    def run(self) -> tuple[RunReport, str]:
        started_at = datetime.now(timezone.utc)
        prompt_template = load_prompt_template(self.config.prompt_template)
        resolved_repo = resolve_repo_target(self.config.repo)

        report = RunReport(
            repo_full_name=resolved_repo.repo_full_name,
            milestone=self.config.milestone,
            started_at=started_at,
        )
        report_path = build_report_path(resolved_repo.repo_full_name, self.config.milestone)
        writer = ReportWriter(report_path)

        try:
            issues = load_open_milestone_issues(resolved_repo.repo_full_name, self.config.milestone)
            if not issues:
                raise ValidationError(
                    f"No open issues found for milestone '{self.config.milestone}'."
                )
            ordered_issues = attach_and_sort_issues(issues)

            for issue in ordered_issues:
                issue_started = datetime.now(timezone.utc)
                print(f"\n[codexor] Starting {issue.key.raw if issue.key else '?'}: {issue.title}")
                prompt = render_prompt(
                    prompt_template,
                    issue=issue,
                    milestone_name=self.config.milestone,
                    repo_full_name=resolved_repo.repo_full_name,
                )
                codex_result = self.codex_runner.run(prompt=prompt, cwd=resolved_repo.local_path)
                signal = parse_final_signal(codex_result.last_non_empty_line)
                issue_finished = datetime.now(timezone.utc)
                duration = int((issue_finished - issue_started).total_seconds())

                if signal == FinalSignal.ALL_DONE:
                    entry = IssueRunResult(
                        issue=issue,
                        started_at=issue_started,
                        finished_at=issue_finished,
                        duration_seconds=duration,
                        status=IssueStatus.DONE,
                        signal=signal,
                        note="Completed with ALL DONE.",
                    )
                    report.entries.append(entry)
                    writer.write(report)
                    continue

                if signal == FinalSignal.BREAK_ON_ERROR:
                    entry = IssueRunResult(
                        issue=issue,
                        started_at=issue_started,
                        finished_at=issue_finished,
                        duration_seconds=duration,
                        status=IssueStatus.BLOCKED,
                        signal=signal,
                        note="Codex requested manual intervention with BREAK ON ERROR.",
                    )
                    report.entries.append(entry)
                    report.finished_at = datetime.now(timezone.utc)
                    report.status = RunStatus.HALTED
                    writer.write(report)
                    return report, str(report_path)

                entry = IssueRunResult(
                    issue=issue,
                    started_at=issue_started,
                    finished_at=issue_finished,
                    duration_seconds=duration,
                    status=IssueStatus.HALTED,
                    signal=signal,
                    note=(
                        "Codex exited without required signal. "
                        f"Last line: {codex_result.last_non_empty_line!r}"
                    ),
                )
                report.entries.append(entry)
                report.finished_at = datetime.now(timezone.utc)
                report.status = RunStatus.HALTED
                writer.write(report)
                return report, str(report_path)

            report.finished_at = datetime.now(timezone.utc)
            report.status = RunStatus.COMPLETED
            writer.write(report)
            return report, str(report_path)
        finally:
            # Keep temporary clones on halted/error runs for manual inspection.
            run_completed = report.status == RunStatus.COMPLETED
            if (
                resolved_repo.is_temporary_clone
                and resolved_repo.cleanup_on_success
                and run_completed
            ):
                cleanup_temporary_repo(resolved_repo.local_path)
