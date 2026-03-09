# Codex-Orchestrator Architecture & Implementation Plan

This document outlines the internal architecture, module design, and technical strategy for implementing the Codex-Orchestrator (`codexor`) CLI. It serves as a blueprint for developers.

## 1. System Overview

`codexor` is a Python 3.11+ CLI application that acts as a stateful controller around the stateless `codex` CLI. It interfaces with the local Git binary and the GitHub CLI (`gh`) to resolve environment state, orchestrates a sequence of subprocesses, and tracks progress in a local file-based report.

**Key Technical Decisions:**
- **Synchronous Execution:** The tool processes one issue at a time in a blocking loop. There is no concurrency.
- **Subprocess Streaming:** Codex output is streamed directly to the terminal (`sys.stdout.buffer`) in real-time, while a background rolling buffer captures the last non-empty line for signal extraction.
- **Stateless Runs:** The orchestrator does not persist resume state. Every invocation evaluates the current GitHub state.

## 2. Component Design & Module Responsibilities

The application is structured into discrete modules, coordinated by a central orchestrator.

### `codexor.models`
Defines immutable data classes used across the application:
- `RunConfig`: Parsed CLI arguments, timestamp, repo data.
- `Issue`: GitHub issue representation (number, title, body).
- `IssueKey`: Parsed key containing `major` (int) and `minor` (str).
- `ReportData`: Accumulator for run-level and per-issue execution metrics.

### `codexor.cli`
- **Responsibility:** Entrypoint and argument parsing (using `argparse`).
- **Implementation:** Parses `--milestone` and `--prompt-template`. Catches top-level exceptions, maps them to canonical diagnostic logs, and calls `sys.exit()` with the correct exit code.

### `codexor.repo`
- **Responsibility:** Git and workspace validation.
- **Implementation:** Executes `git status --porcelain` to ensure a clean worktree. Executes `gh repo view --json nameWithOwner` to extract the repository identity. Raises specific dependency exceptions on failure.

### `codexor.github`
- **Responsibility:** Interfacing with the GitHub CLI.
- **Implementation:**
  - Executes `gh issue list --milestone <id> --state open --json number,title,body` to fetch the target workload.
  - Returns a list of `Issue` models.

### `codexor.issue_key`
- **Responsibility:** Parsing, validating, and sorting issue keys.
- **Implementation:** 
  - Applies regex `\bM(?P<major>\d+)-(?P<minor>\d+)\b` (case-insensitive).
  - Validates that each issue title contains exactly one match.
  - Validates uniqueness across the milestone set using a `set`.
  - Sorts issues based on the tuple `(int(major), str(minor))` (e.g., `M4-05` < `M4-051` < `M4-06`).

### `codexor.template`
- **Responsibility:** Prompt rendering.
- **Implementation:**
  - Reads the user-provided Markdown snippet.
  - Uses basic string replacement or a lightweight regex to replace the exact defined placeholders.
  - Validates that no unknown `{{...}}` placeholders exist.
  - Handles the internal static prompt file used for closing the milestone.

### `codexor.codex_runner`
- **Responsibility:** Subprocess lifecycle and terminal I/O.
- **Implementation:**
  - Uses `subprocess.Popen` to launch `codex --yolo --no-alt-screen`.
  - Reads `stdout` and `stderr` streams, writing them directly to `sys.stdout.buffer` to preserve ANSI colors and interactive TTY behavior.
  - Maintains a rolling buffer of the decoded output to capture the last non-empty line upon process exit.
  - **Signal Handling:** Hooks into `SIGINT` (Ctrl+C). Forwards the interrupt to the child process, waits up to 10 seconds, and invokes `process.kill()` (or `TerminateProcess` on Windows) if the child hasn't cleanly exited.

### `codexor.signals`
- **Responsibility:** Final signal extraction.
- **Implementation:**
  - Receives the final non-empty line from the runner.
  - Strips all ANSI escape codes using a regex (e.g., `\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])`).
  - Strips leading/trailing whitespace.
  - Returns an enum: `ALL_DONE`, `BREAK_ON_ERROR`, or `INVALID`.

### `codexor.reporting`
- **Responsibility:** Disk-based progress tracking.
- **Implementation:**
  - Determines path: `~/.codexor/reports/<repo_slug>__<milestone_slug>__<timestamp>.md`.
  - Writes the Markdown report. Called incrementally after every issue completes to ensure data is not lost on crash.

### `codexor.orchestrator`
- **Responsibility:** The core state machine governing the run lifecycle.
- **Implementation:** Loops over sorted issues, instantiates the runner, evaluates the resulting signal, updates the report, and decides whether to transition to the next issue, halt, or execute the milestone closure protocol.

## 3. Milestone Closure Protocol

When the orchestrator successfully processes all open issues in the milestone (all returned `ALL DONE`), it triggers the closure sequence:
1. The orchestrator loads an internal, pre-packaged prompt file (e.g., `codexor/prompts/close_milestone.md`).
2. The orchestrator renders this prompt, inserting the milestone identifier into a placeholder.
3. The orchestrator invokes `codexor.codex_runner` with this rendered prompt. This process streams to the terminal exactly like a normal issue.
4. Codex executes the necessary `gh` commands to close the milestone and must emit the `ALL DONE` signal upon success.
5. Once this final Codex process completes successfully, the run is marked as `completed` (Exit Code 0).

## 4. Execution State Machine

The `Orchestrator` implements the following logical states:

- **`INIT`**: Resolving args, validating repo, loading issues.
  - *Transitions to:* `RUNNING_ISSUE` (success) | `FAILED_CONFIG` (bad template/keys) | `FAILED_DEPENDENCY` (git/gh unavailable).
- **`RUNNING_ISSUE`**: Codex subprocess is active for the current issue.
  - *Transitions to:* `EVALUATING_SIGNAL` (process exited) | `INTERRUPTED` (Ctrl+C).
- **`EVALUATING_SIGNAL`**: Parsing the last line.
  - *Transitions to:*
    - `RUNNING_ISSUE` (Signal `ALL DONE`, more issues remain).
    - `CLOSING_MILESTONE` (Signal `ALL DONE`, no issues remain).
    - `BLOCKED` (Signal `BREAK ON ERROR`).
    - `HALTED` (Signal `INVALID`).
- **`CLOSING_MILESTONE`**: Running the internal milestone closure prompt.
  - *Transitions to:* `COMPLETED` (success) | `HALTED` (failure).

## 5. Diagnostic Logging Contract

To ensure the CLI is easily consumable by wrapper scripts or CI pipelines, all fatal errors terminating the application must emit exactly one canonical, parseable log line to `stderr` before exiting:

```text
[codexor] level=error code=<error_code> run_status=<run_status> exit_code=<exit_code> detail="<message>"
```

*Example:*
`[codexor] level=error code=invalid_keys run_status=failed_config exit_code=4 detail="Duplicate issue key M2-04 found in milestone."`