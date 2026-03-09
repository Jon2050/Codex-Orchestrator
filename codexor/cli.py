"""CLI entry point for codexor."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .errors import CodexorError
from .models import RunConfig
from .orchestrator import Orchestrator


def build_parser() -> argparse.ArgumentParser:
    """Build CLI parser."""
    parser = argparse.ArgumentParser(
        prog="codexor",
        description="Sequential milestone orchestrator for Codex issue implementation.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run milestone automation.")
    run_parser.add_argument("--milestone", required=True, help="Milestone name.")
    run_parser.add_argument(
        "--prompt-template",
        required=True,
        help="Path to prompt snippet template file.",
    )
    run_parser.add_argument(
        "--cli",
        default="codex",
        help="The AI CLI tool to execute (e.g. codex, gemini, claude). Defaults to codex.",
    )
    return parser


def emit_diagnostic(error_code: str, run_status: str, exit_code: int, detail: str) -> None:
    """Emit canonical diagnostic log line for fatal errors."""
    detail = detail.replace("\n", " ").replace('"', "'")
    print(
        f'[codexor] level=error code={error_code} run_status={run_status} exit_code={exit_code} detail="{detail}"',
        file=sys.stderr,
    )


def main(argv: list[str] | None = None) -> int:
    """CLI main function."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command != "run":
        parser.print_help()
        return 4

    config = RunConfig(
        cwd=Path.cwd(),
        milestone=args.milestone,
        prompt_template=Path(args.prompt_template),
        cli_tool=args.cli,
    )

    from .errors import DirtyWorktreeError, ExternalCommandError, ValidationError

    try:
        orchestrator = Orchestrator(config)
        report, report_path = orchestrator.run()
    except ValidationError as exc:
        emit_diagnostic("invalid_config", "failed_config", 4, str(exc))
        return 4
    except ExternalCommandError as exc:
        emit_diagnostic("dependency_error", "failed_dependency", 5, str(exc))
        return 5
    except DirtyWorktreeError as exc:
        emit_diagnostic("dirty_worktree", "failed_dependency", 5, str(exc))
        return 5
    except CodexorError as exc:
        emit_diagnostic("internal_error", "halted", 1, str(exc))
        return 1
    except KeyboardInterrupt:
        emit_diagnostic("interrupted", "interrupted", 130, "Operator interrupt.")
        return 130
    except Exception as exc:
        emit_diagnostic("unexpected_error", "halted", 1, str(exc))
        return 1

    print("")
    print(f"[codexor] Run status: {report.status.value if report.status else 'unknown'}")
    print(f"[codexor] Report: {report_path}")
    
    if report.status and report.status.value == "completed":
        return 0
    elif report.status and report.status.value == "blocked":
        return 2
    elif report.status and report.status.value == "halted":
        # Check if any issue was halted due to invalid signal vs unexpected internal error
        from .models import IssueStatus
        for entry in report.entries:
            if entry.status == IssueStatus.HALTED:
                return 3
        return 1
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
