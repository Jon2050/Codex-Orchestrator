"""Prompt template validation and rendering."""

from __future__ import annotations

import re
from pathlib import Path

from .errors import ValidationError
from .models import MilestoneIssue

PLACEHOLDER_PATTERN = re.compile(r"{{\s*([A-Z0-9_]+)\s*}}")
SUPPORTED_PLACEHOLDERS = {
    "ISSUE_KEY",
    "ISSUE_NUMBER",
    "ISSUE_TITLE",
    "ISSUE_BODY",
    "MILESTONE_NAME",
    "REPO_FULL_NAME",
}


def load_prompt_template(path: Path) -> str:
    """Load and validate a prompt template file."""
    resolved = path.expanduser().resolve()
    if not resolved.exists() or not resolved.is_file():
        raise ValidationError(f"Prompt template file does not exist: {resolved}")

    content = resolved.read_text(encoding="utf-8")
    
    # Hide escaped braces to not treat them as placeholders during validation
    content_for_validation = content.replace("{{{{", "\x01").replace("}}}}", "\x02")
    
    found = set(PLACEHOLDER_PATTERN.findall(content_for_validation))
    unsupported = sorted(found - SUPPORTED_PLACEHOLDERS)
    if unsupported:
        joined = ", ".join(unsupported)
        raise ValidationError(f"Unsupported placeholders in template: {joined}")
    return content


def render_prompt(
    template: str,
    *,
    issue: MilestoneIssue,
    milestone_name: str,
    repo_full_name: str,
) -> str:
    """Render one issue prompt from template and metadata."""
    if not issue.key:
        raise ValidationError(f"Issue key is missing for issue #{issue.number}: {issue.title}")

    mapping = {
        "ISSUE_KEY": issue.key.raw,
        "ISSUE_NUMBER": str(issue.number),
        "ISSUE_TITLE": issue.title,
        "ISSUE_BODY": issue.body,
        "MILESTONE_NAME": milestone_name,
        "REPO_FULL_NAME": repo_full_name,
    }

    # Hide escaped braces
    temp_rendered = template.replace("{{{{", "\x01").replace("}}}}", "\x02")

    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        return mapping[name]

    temp_rendered = PLACEHOLDER_PATTERN.sub(replace, temp_rendered)
    
    # Restore escaped braces
    return temp_rendered.replace("\x01", "{{").replace("\x02", "}}")
