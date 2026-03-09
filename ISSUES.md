# Codex-Orchestrator Task List

This document tracks all tasks required to fully implement `codexor` according to the core requirements, architecture, and README.

## Core Setup & Configuration
- [x] **Setup Project Structure**: Define package modules, classes, and setup `pyproject.toml` with entry points.
- [x] **Setup Pytest**: Implement simple tests with Pytest suite.
- [x] **Define Data Models**: Implement `RunConfig`, `Issue`, `IssueKey`, and `ReportData` models in `codexor.models`.

## CLI & Error Handling
- [x] **Implement `codexor.cli` Module**: Parse `--milestone` and `--prompt-template` arguments using `argparse`.
- [x] **Default Working Directory**: Update CLI to use `cwd` instead of `--repo`.
- [x] **Implement Diagnostic Logging**: Format all fatal errors as parseable, single-line messages (`[codexor] level=error code=<error_code> ...`).
- [x] **Define Canonical Exit Codes**: Ensure the application cleanly exits using standard codes (0=completed, 1=halted, 2=blocked, 3=invalid signal, 4=failed config, 5=failed dependency, 130=interrupted).

## Git & Workspace Validation
- [x] **Implement `codexor.repo` Module**: Add validation to ensure execution inside a git repository.
- [x] **Validate Clean Worktree**: Check `git status --porcelain` to block execution if uncommitted changes exist.
- [x] **Resolve GitHub Context**: Extract the current owner/repo using the `gh repo view` command.

## GitHub Integration
- [x] **Implement `codexor.github` Module**: Load open issues for a target milestone.
- [x] **Extract Issue Payloads**: Run `gh issue list` and parse the JSON payload for `number`, `title`, `body`, and `url`.

## Issue Processing & Keys
- [x] **Implement `codexor.issue_key` Module**: Extract the specific pattern `\bM(?P<major>\d+)-(?P<minor>\d+)\b`.
- [x] **Enforce Key Uniqueness**: Validate that no duplicate issue keys exist within the milestone. Fail fast (`failed_config`) if duplicates are detected.
- [x] **Enforce Single Key Requirement**: Verify that each issue title has exactly one key.
- [x] **Deterministic Sorting**: Ensure all issues process in deterministic, sorted order based on the `(major, minor)` tuple.
- [x] **Display Initial Ordered List**: Print the complete sorted list of issue numbers and titles at startup.

## Prompt Templating
- [x] **Implement `codexor.template` Module**: Load and validate the provided Markdown snippet.
- [x] **Render Placeholders**: Render `{{ISSUE_KEY}}`, `{{ISSUE_NUMBER}}`, `{{ISSUE_TITLE}}`, `{{ISSUE_BODY}}`, `{{MILESTONE_NAME}}`, and `{{REPO_FULL_NAME}}`.
- [x] **Implement Literal Braces Parsing**: Correctly escape `{{{{` to `{{` and `}}}}` to `}}` without throwing placeholder validation errors.
- [x] **Block Unknown Placeholders**: Throw a validation error if any unsupported placeholder is identified.

## Subprocess Execution & Streaming
- [x] **Implement `codexor.codex_runner`**: Run `codex --yolo --no-alt-screen` using `subprocess.Popen`.
- [x] **Stream Real-time IO**: Direct output strictly to `sys.stdout.buffer` for maintaining colors/TTY, while proxying `sys.stdin` for real-time input.
- [x] **Track Output Tail**: Maintain a thread-safe rolling buffer to perfectly capture the final non-empty line emitted upon process completion.
- [x] **Handle KeyboardInterrupt (Ctrl+C)**: Hook `SIGINT` to gracefully send the signal to the child subprocess, waiting exactly 10 seconds before force-killing.

## Handshake Protocol & Signaling
- [x] **Implement `codexor.signals` Module**: Cleanse ANSI escape codes and whitespace from the captured tail output.
- [x] **Extract Final Signal Enum**: Read the line for exactly `ALL DONE` or `BREAK ON ERROR`.
- [x] **Enforce Halt Policies**:
  - Transition to **completed** for `ALL DONE`.
  - Transition to **blocked** for `BREAK ON ERROR` (exit code 2).
  - Transition to **halted** on any invalid or missing signal (exit code 3).

## Milestone Completion Protocol
- [x] **Package Static Prompts**: Embed `prompts/close_milestone.md` inside the Python package metadata.
- [x] **Close Milestone Logic**: When all issues return `ALL DONE`, silently invoke a Codex process loaded with `close_milestone.md` to run `gh` closure commands natively.

## Reporting & Markdown Output
- [x] **Implement `codexor.reporting` Module**: Setup persistent, out-of-band disk reporting stored globally at `~/.codexor/reports/`.
- [x] **Assemble the Filename**: Structure paths with project ident, milestone slug, and timestamps.
- [x] **Format Run-Level Metrics**: Include metadata for `run_id`, repo, milestone, `run_status`, timestamps, and run duration.
- [x] **Format Per-Issue Markdown Table**: Append metadata headers correctly mapping out: `Issue Key`, `Number`, `Title`, `Start`, `End`, `Duration (s)`, `Status`, `Signal`, and `Problems`.
- [x] **Incremental File Writes**: Push table updates incrementally so reports survive unexpected run crashes.

## Final Review & Validation
- [x] Build and test fully on a target project checking all dependencies and requirements.
- [x] Verify terminal rendering fidelity when piping streaming processes.
- [x] Verify complete compliance with architecture limits.