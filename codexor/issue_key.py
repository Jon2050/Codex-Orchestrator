"""Issue key parsing and deterministic sorting."""

from __future__ import annotations

import re

from .errors import ValidationError
from .models import IssueKey, MilestoneIssue

ISSUE_KEY_PATTERN = re.compile(r"\b(M(?P<major>\d+)-(?P<minor>\d+))\b", flags=re.IGNORECASE)


def parse_issue_key(title: str) -> IssueKey:
    """Parse an issue key like M4-051 from an issue title."""
    matches = list(ISSUE_KEY_PATTERN.finditer(title))
    if not matches:
        raise ValidationError(f"Issue title has no parseable key: {title}")
    if len(matches) > 1:
        raise ValidationError(f"Issue title has multiple parseable keys, exactly one is required: {title}")

    match = matches[0]
    raw = match.group(1).upper()
    major = int(match.group("major"))
    minor = match.group("minor")
    return IssueKey(raw=raw, major=major, minor=minor)


def attach_and_sort_issues(issues: list[MilestoneIssue]) -> list[MilestoneIssue]:
    """Parse issue keys for all issues and return deterministic issue-key ordering."""
    enriched: list[MilestoneIssue] = []
    seen_keys: set[str] = set()

    for issue in issues:
        issue.key = parse_issue_key(issue.title)
        if issue.key.raw in seen_keys:
            raise ValidationError(f"Duplicate issue key {issue.key.raw} found in milestone.")
        seen_keys.add(issue.key.raw)
        enriched.append(issue)

    return sorted(
        enriched,
        key=lambda issue: (
            issue.key.sort_tuple if issue.key else (0, ()),
            issue.number,
        ),
    )
