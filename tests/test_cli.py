from unittest.mock import patch
import pytest

from codexor.cli import build_parser, main

def test_build_parser():
    parser = build_parser()
    args = parser.parse_args(["run", "--milestone", "M1", "--prompt-template", "prompt.md"])
    assert args.command == "run"
    assert args.milestone == "M1"
    assert args.prompt_template == "prompt.md"

@patch("codexor.cli.Orchestrator")
@patch("codexor.cli.Path.cwd")
def test_main_completed(mock_cwd, mock_orchestrator):
    mock_cwd.return_value = "dummy"
    
    mock_instance = mock_orchestrator.return_value
    
    class MockStatus:
        value = "completed"
        
    class MockReport:
        status = MockStatus()
        entries = []
        
    mock_instance.run.return_value = (MockReport(), "path/to/report.md")
    
    exit_code = main(["run", "--milestone", "M1", "--prompt-template", "prompt.md"])
    
    assert exit_code == 0

@patch("codexor.cli.Orchestrator")
@patch("codexor.cli.Path.cwd")
def test_main_blocked(mock_cwd, mock_orchestrator):
    mock_cwd.return_value = "dummy"
    
    mock_instance = mock_orchestrator.return_value
    
    class MockStatus:
        value = "blocked"
        
    class MockReport:
        status = MockStatus()
        entries = []
        
    mock_instance.run.return_value = (MockReport(), "path/to/report.md")
    
    exit_code = main(["run", "--milestone", "M1", "--prompt-template", "prompt.md"])
    
    assert exit_code == 2

from codexor.errors import ValidationError
@patch("codexor.cli.Orchestrator")
def test_main_validation_error(mock_orchestrator):
    mock_orchestrator.side_effect = ValidationError("Invalid stuff")
    exit_code = main(["run", "--milestone", "M1", "--prompt-template", "prompt.md"])
    assert exit_code == 4