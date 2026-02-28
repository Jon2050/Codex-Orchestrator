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
    run_parser.add_argument("--repo", required=True, help="Local repo path or owner/repo.")
    run_parser.add_argument("--milestone", required=True, help="Milestone name.")
    run_parser.add_argument(
        "--prompt-template",
        required=True,
        help="Path to prompt snippet template file.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI main function."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command != "run":
        parser.print_help()
        return 2

    config = RunConfig(
        repo=args.repo,
        milestone=args.milestone,
        prompt_template=Path(args.prompt_template),
    )

    try:
        orchestrator = Orchestrator(config)
        report, report_path = orchestrator.run()
    except CodexorError as exc:
        print(f"[codexor] ERROR: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n[codexor] Interrupted by user.", file=sys.stderr)
        return 130

    print("")
    print(f"[codexor] Run status: {report.status.value if report.status else 'unknown'}")
    print(f"[codexor] Report: {report_path}")
    return 0 if report.status and report.status.value == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
