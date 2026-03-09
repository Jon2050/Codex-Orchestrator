from pathlib import Path

from codexor.errors import ValidationError
from codexor.models import IssueKey, MilestoneIssue
from codexor.template import load_prompt_template, render_prompt


def test_load_prompt_template_rejects_unsupported_placeholder(tmp_path: Path) -> None:
    file_path = tmp_path / "prompt.md"
    file_path.write_text("Task {{ISSUE_KEY}} {{UNKNOWN}}", encoding="utf-8")

    try:
        load_prompt_template(file_path)
    except ValidationError:
        return
    raise AssertionError("Expected ValidationError for unsupported placeholders.")


def test_render_prompt_replaces_all_supported_placeholders() -> None:
    issue = MilestoneIssue(
        number=17,
        title="M2-03 Create deploy workflow",
        body="This is the body",
        url="https://example/17",
        key=IssueKey(raw="M2-03", major=2, minor="03"),
    )
    template = (
        "Task {{ISSUE_KEY}} #{{ISSUE_NUMBER}} {{ISSUE_TITLE}} "
        "{{MILESTONE_NAME}} {{REPO_FULL_NAME}}\n"
        "Body: {{ISSUE_BODY}}\n"
        "Literal {{{{escaped}}}}"
    )
    rendered = render_prompt(
        template,
        issue=issue,
        milestone_name="M2 - Deploy",
        repo_full_name="example/repo",
    )
    assert "M2-03" in rendered
    assert "#17" in rendered
    assert "M2 - Deploy" in rendered
    assert "example/repo" in rendered
    assert "This is the body" in rendered
    assert "Literal {{escaped}}" in rendered
