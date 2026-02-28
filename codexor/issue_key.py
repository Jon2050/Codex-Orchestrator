"""Issue key parsing and deterministic sorting."""

from __future__ import annotations

import re

from .errors import ValidationError
from .models import IssueKey, MilestoneIssue

ISSUE_KEY_PATTERN = re.compile(r"\b(M(?P<major>\d+)-(?P<minor>\d+))\b", flags=re.IGNORECASE)


def parse_issue_key(title: str) -> IssueKey:
    """Parse an issue key like M4-051 from an issue title."""
    match = ISSUE_KEY_PATTERN.search(title)
    if not match:
        raise ValidationError(f"Issue title has no parseable key: {title}")

    raw = match.group(1).upper()
    major = int(match.group("major"))
    minor = match.group("minor")
    return IssueKey(raw=raw, major=major, minor=minor)


def attach_and_sort_issues(issues: list[MilestoneIssue]) -> list[MilestoneIssue]:
    """Parse issue keys for all issues and return deterministic issue-key ordering."""
    enriched: list[MilestoneIssue] = []
    for issue in issues:
        issue.key = parse_issue_key(issue.title)
        enriched.append(issue)

    return sorted(
        enriched,
        key=lambda issue: (
            issue.key.sort_tuple if issue.key else (0, ()),
            issue.number,
        ),
    )
