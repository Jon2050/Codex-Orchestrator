"""Run controller and state machine."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

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
    MilestoneIssue,
)
from .reporting import ReportWriter, build_report_path
from .repo import resolve_repo_target
from .signals import parse_final_signal, parse_summary
from .template import load_prompt_template, render_prompt


class Orchestrator:
    """Coordinates end-to-end milestone issue execution."""

    def __init__(self, config: RunConfig) -> None:
        self.config = config
        self.codex_runner = CodexRunner(cli_tool=config.cli_tool)

    def run(self) -> tuple[RunReport, str]:
        started_at = datetime.now(timezone.utc)
        prompt_template = load_prompt_template(self.config.prompt_template)
        resolved_repo = resolve_repo_target(self.config.cwd)

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
            ordered_issues = attach_and_sort_issues(issues, self.config.milestone)
            
            print(f"[codexor] Ordered issues for milestone '{self.config.milestone}':")
            for issue in ordered_issues:
                print(f"  - #{issue.number}: {issue.title}")
                
            print("")
            try:
                input("[codexor] Press Enter to begin execution or Ctrl+C to abort... ")
            except EOFError:
                pass # Continue if running in non-interactive mode where stdin is closed

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
                print(f"DEBUG: Output tail: {codex_result.output_tail!r}")
                signal = parse_final_signal(codex_result.output_tail)
                print(f"[codexor] Signal received: {signal.value}")
                summary = parse_summary(codex_result.output_tail)
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
                        summary=summary,
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
                        summary=summary,
                    )
                    report.entries.append(entry)
                    report.finished_at = datetime.now(timezone.utc)
                    report.status = RunStatus.BLOCKED
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
                    summary=summary,
                )
                report.entries.append(entry)
                report.finished_at = datetime.now(timezone.utc)
                report.status = RunStatus.HALTED
                writer.write(report)
                return report, str(report_path)

            # All issues completed successfully. Close the milestone.
            print(f"\n[codexor] Closing milestone '{self.config.milestone}'...")
            close_milestone_template_path = Path(__file__).parent / "prompts" / "close_milestone.md"
            if close_milestone_template_path.exists():
                close_prompt_template = close_milestone_template_path.read_text(encoding="utf-8")
            else:
                raise ValidationError("Missing internal close_milestone.md prompt.")
                
            dummy_issue = MilestoneIssue(number=0, title="Close Milestone", body="", url="", key=None)
            close_prompt = close_prompt_template.replace("{{MILESTONE_NAME}}", self.config.milestone).replace("{{REPO_FULL_NAME}}", resolved_repo.repo_full_name)
            
            close_result = self.codex_runner.run(prompt=close_prompt, cwd=resolved_repo.local_path)
            close_signal = parse_final_signal(close_result.output_tail)
            
            if close_signal != FinalSignal.ALL_DONE:
                 report.finished_at = datetime.now(timezone.utc)
                 report.status = RunStatus.HALTED
                 writer.write(report)
                 return report, str(report_path)

            report.finished_at = datetime.now(timezone.utc)
            report.status = RunStatus.COMPLETED
            writer.write(report)
            return report, str(report_path)
            
        except KeyboardInterrupt:
            report.finished_at = datetime.now(timezone.utc)
            report.status = RunStatus.INTERRUPTED
            writer.write(report)
            raise
        except Exception:
            report.finished_at = datetime.now(timezone.utc)
            report.status = RunStatus.HALTED
            writer.write(report)
            raise
