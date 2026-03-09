import json
from unittest.mock import patch

from codexor.github import resolve_repo_full_name, load_open_milestone_issues
from codexor.models import MilestoneIssue
from pathlib import Path

@patch("codexor.github.run_command")
def test_resolve_repo_full_name(mock_run):
    mock_run.return_value = "owner/repo\n"
    result = resolve_repo_full_name(Path("."))
    assert result == "owner/repo"
    mock_run.assert_called_once()

@patch("codexor.github.run_command")
def test_load_open_milestone_issues(mock_run):
    mock_response = [
        {
            "number": 1,
            "title": "M1-01 First",
            "body": "Description",
            "url": "https://example.com/1"
        }
    ]
    mock_run.return_value = json.dumps(mock_response)
    
    issues = load_open_milestone_issues("owner/repo", "M1")
    
    assert len(issues) == 1
    assert issues[0].number == 1
    assert issues[0].title == "M1-01 First"
    assert issues[0].body == "Description"
    assert issues[0].url == "https://example.com/1"
    
    args, kwargs = mock_run.call_args
    assert "gh" in args[0]
    assert "issue" in args[0]
    assert "--repo" in args[0]
    assert "owner/repo" in args[0]
    assert "--milestone" in args[0]
    assert "M1" in args[0]