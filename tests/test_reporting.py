from datetime import datetime, timezone

from codexor.models import (
    FinalSignal,
    IssueKey,
    IssueRunResult,
    IssueStatus,
    MilestoneIssue,
    RunReport,
    RunStatus,
)
from codexor.reporting import render_report_markdown


def test_render_report_markdown_includes_table_row() -> None:
    started = datetime(2026, 2, 28, 7, 0, 0, tzinfo=timezone.utc)
    finished = datetime(2026, 2, 28, 7, 5, 0, tzinfo=timezone.utc)
    issue = MilestoneIssue(
        number=21,
        title="M2-05 Add deployment smoke checks",
        url="https://example/21",
        key=IssueKey(raw="M2-05", major=2, minor="05"),
    )
    entry = IssueRunResult(
        issue=issue,
        started_at=started,
        finished_at=finished,
        duration_seconds=300,
        status=IssueStatus.DONE,
        signal=FinalSignal.ALL_DONE,
        note="Completed.",
    )
    report = RunReport(
        repo_full_name="owner/repo",
        milestone="M2 - Deploy",
        started_at=started,
        finished_at=finished,
        status=RunStatus.COMPLETED,
        entries=[entry],
    )

    markdown = render_report_markdown(report)
    assert "# codexor run report: owner/repo / M2 - Deploy" in markdown
    assert "| M2-05 | #21 | M2-05 Add deployment smoke checks |" in markdown
