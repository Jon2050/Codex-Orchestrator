from codexor.errors import ValidationError
from codexor.issue_key import attach_and_sort_issues, parse_issue_key
from codexor.models import MilestoneIssue


def test_parse_issue_key_success() -> None:
    parsed = parse_issue_key("M4-051 Integrate pipeline")
    assert parsed.raw == "M4-051"
    assert parsed.major == 4
    assert parsed.minor == "051"


def test_parse_issue_key_missing_raises() -> None:
    try:
        parse_issue_key("No milestone key in title")
    except ValidationError:
        return
    raise AssertionError("Expected ValidationError when key is missing.")


def test_attach_and_sort_issues_uses_issue_key_order() -> None:
    issues = [
        MilestoneIssue(number=3, title="M4-06 Third", body="body", url="https://example/3"),
        MilestoneIssue(number=1, title="M4-05 First", body="body", url="https://example/1"),
        MilestoneIssue(number=2, title="M4-051 Second", body="body", url="https://example/2"),
    ]
    ordered = attach_and_sort_issues(issues, "M4")
    ordered_keys = [issue.key.raw for issue in ordered if issue.key]
    assert ordered_keys == ["M4-05", "M4-051", "M4-06"]


def test_attach_and_sort_issues_invalid_milestone() -> None:
    issues = [
        MilestoneIssue(number=1, title="M1-05 First", body="body", url="https://example/1"),
    ]
    try:
        attach_and_sort_issues(issues, "M4")
    except ValidationError as e:
        assert "does not match the target milestone 'M4' (M4)" in str(e)
        return
    raise AssertionError("Expected ValidationError when issue key does not match milestone.")
