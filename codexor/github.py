"""GitHub issue loading via gh CLI."""

from __future__ import annotations

import json
from pathlib import Path

from .command import run_command
from .models import MilestoneIssue


def resolve_repo_full_name(local_repo_path: Path) -> str:
    """Resolve owner/repo from current local repository using gh."""
    output = run_command(
        [
            "gh",
            "repo",
            "view",
            "--json",
            "nameWithOwner",
            "--jq",
            ".nameWithOwner",
        ],
        cwd=local_repo_path,
    )
    return output.strip()


def load_open_milestone_issues(repo_full_name: str, milestone_name: str) -> list[MilestoneIssue]:
    """Load open issues for a milestone from GitHub."""
    output = run_command(
        [
            "gh",
            "issue",
            "list",
            "--repo",
            repo_full_name,
            "--milestone",
            milestone_name,
            "--state",
            "open",
            "--limit",
            "500",
            "--json",
            "number,title,body,url",
        ]
    )
    payload = json.loads(output)
    return [
        MilestoneIssue(
            number=int(item["number"]),
            title=str(item["title"]),
            body=str(item.get("body", "")),
            url=str(item["url"]),
        )
        for item in payload
    ]
