"""Issue key parsing and deterministic sorting."""

from __future__ import annotations

import re

from .errors import ValidationError
from .models import IssueKey, MilestoneIssue

ISSUE_KEY_PATTERN = re.compile(r"\b(M(?P<major>\d+)-(?P<minor>\d+))\b", flags=re.IGNORECASE)


def parse_issue_key(title: str) -> IssueKey | None:
    """Parse an issue key like M4-051 from an issue title. Returns None if invalid."""
    matches = list(ISSUE_KEY_PATTERN.finditer(title))
    if not matches or len(matches) > 1:
        return None

    match = matches[0]
    raw = match.group(1).upper()
    major = int(match.group("major"))
    minor = match.group("minor")
    return IssueKey(raw=raw, major=major, minor=minor)


def attach_and_sort_issues(issues: list[MilestoneIssue], milestone_name: str) -> list[MilestoneIssue]:
    """Parse issue keys for all issues and return deterministic issue-key ordering, filtering out invalid issues."""
    enriched: list[MilestoneIssue] = []
    seen_keys: set[str] = set()

    # Extract the expected M<major> prefix from the milestone name.
    milestone_match = re.match(r"^(M\d+)", milestone_name.strip(), flags=re.IGNORECASE)
    expected_prefix = milestone_match.group(1).upper() if milestone_match else None

    for issue in issues:
        issue.key = parse_issue_key(issue.title)
        
        if not issue.key:
            continue
        
        # Filter out issues that do not match the target milestone
        if expected_prefix:
            issue_prefix = f"M{issue.key.major}"
            if issue_prefix != expected_prefix:
                continue

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
