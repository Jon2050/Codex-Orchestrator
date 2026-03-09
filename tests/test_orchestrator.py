from unittest.mock import patch, MagicMock
from pathlib import Path
from codexor.orchestrator import Orchestrator
from codexor.models import RunConfig, CodexRunResult, FinalSignal, RunStatus, MilestoneIssue

@patch("builtins.input", return_value="")
@patch("codexor.orchestrator.resolve_repo_target")
@patch("codexor.orchestrator.load_open_milestone_issues")
@patch("codexor.orchestrator.CodexRunner")
@patch("codexor.orchestrator.ReportWriter")
def test_orchestrator_successful_run(
    mock_report_writer,
    mock_runner_cls,
    mock_load_issues,
    mock_resolve_target,
    mock_input,
    tmp_path,
):
    prompt_path = tmp_path / "prompt.md"
    prompt_path.write_text("Task: {{ISSUE_TITLE}}")
    config = RunConfig(cwd=tmp_path, milestone="M1", prompt_template=prompt_path)
    
    # Mock Repo
    mock_repo = MagicMock()
    mock_repo.repo_full_name = "owner/repo"
    mock_repo.local_path = tmp_path
    mock_resolve_target.return_value = mock_repo
    
    # Mock Issues
    mock_load_issues.return_value = [
        MilestoneIssue(number=1, title="M1-01 Task 1", body="b", url="u")
    ]
    
    # Mock Runner
    mock_runner = mock_runner_cls.return_value
    mock_runner.run.side_effect = [
        CodexRunResult(exit_code=0, last_non_empty_line="ALL DONE", output_tail="ALL DONE"),
        CodexRunResult(exit_code=0, last_non_empty_line="ALL DONE", output_tail="ALL DONE"), # for close milestone
    ]
    
    # Needs to mock the internal prompt for closing milestone
    with patch("codexor.orchestrator.Path.exists") as mock_exists:
        with patch("codexor.orchestrator.Path.read_text") as mock_read_text:
            mock_exists.return_value = True
            mock_read_text.return_value = "Close Milestone Prompt"
            
            orchestrator = Orchestrator(config)
            report, report_path = orchestrator.run()

    assert report.status == RunStatus.COMPLETED
    assert len(report.entries) == 1
    assert report.entries[0].signal == FinalSignal.ALL_DONE

@patch("builtins.input", return_value="")
@patch("codexor.orchestrator.resolve_repo_target")
@patch("codexor.orchestrator.load_open_milestone_issues")
@patch("codexor.orchestrator.CodexRunner")
@patch("codexor.orchestrator.ReportWriter")
def test_orchestrator_blocked_run(
    mock_report_writer,
    mock_runner_cls,
    mock_load_issues,
    mock_resolve_target,
    mock_input,
    tmp_path,
):
    prompt_path = tmp_path / "prompt.md"
    prompt_path.write_text("Task: {{ISSUE_TITLE}}")
    config = RunConfig(cwd=tmp_path, milestone="M1", prompt_template=prompt_path)
    
    # Mock Repo
    mock_repo = MagicMock()
    mock_repo.repo_full_name = "owner/repo"
    mock_repo.local_path = tmp_path
    mock_resolve_target.return_value = mock_repo
    
    # Mock Issues
    mock_load_issues.return_value = [
        MilestoneIssue(number=1, title="M1-01 Task 1", body="b", url="u")
    ]
    
    # Mock Runner
    mock_runner = mock_runner_cls.return_value
    mock_runner.run.return_value = CodexRunResult(exit_code=0, last_non_empty_line="BREAK ON ERROR", output_tail="BREAK ON ERROR")
    
    orchestrator = Orchestrator(config)
    report, report_path = orchestrator.run()

    assert report.status == RunStatus.BLOCKED
    assert len(report.entries) == 1
    assert report.entries[0].signal == FinalSignal.BREAK_ON_ERROR