# Codex-Orchestrator Requirements

## 1. Purpose & Scope Boundary

Codex-Orchestrator shall automate end-to-end processing of GitHub issues by milestone, one issue at a time, enforcing delivery gates via fresh Codex sessions. The system is strictly for executing implementation work, not for project or milestone planning.

## 2. Functional Requirements

### FR-01 Core Execution
- The system shall accept a milestone identifier and a prompt snippet file. If the template is missing/invalid, fail fast (`failed_config`).
- The system shall run inside a checked-out git repository with a clean worktree.
- The system shall validate the milestone exists, load open issues, and print all issues with number and title in correct order at startup.

### FR-02 Issue Processing & Ordering
- Issues shall be processed sequentially in deterministic order based on issue keys.
- **Issue-Key Parsing:** Keys must match `\bM(?P<major>\d+)-(?P<minor>\d+)\b` (case-insensitive). Titles must have exactly one key. Duplicate keys within the milestone are invalid and shall fail validation before processing.

### FR-03 Prompt Rendering
- Allowed placeholders: `{{ISSUE_KEY}}`, `{{ISSUE_NUMBER}}`, `{{ISSUE_TITLE}}`, `{{ISSUE_BODY}}`, `{{MILESTONE_NAME}}`, `{{REPO_FULL_NAME}}`.
- Literal `{{` or `}}` must be escaped as `{{{{` and `}}}}`.
- Unknown placeholders shall fail validation.

### FR-04 Session Isolation & Signal Protocol
- Each issue shall start a brand-new Codex subprocess.
- The orchestrator requires an explicit final signal from the last non-empty output line of the Codex process:
  - `ALL DONE`: Successful completion.
  - `BREAK ON ERROR`: Blocked/manual-intervention state.
- If no valid signal is present, the issue is marked `halted` and the run terminates.

### FR-05 Prompt-Delegated Behaviors
The orchestrator delegates the following responsibilities to Codex via the prompt template instructions. The orchestrator does not directly verify these actions:
- Iterative quality loops (implement, test, review, fix).
- Enforcement of acceptance criteria.
- Git branch management (creation, auto-merge, deletion).
- Issue closure.
- CI/workflow validation.
- Quota/rate-limit handling.

### FR-06 Blocker & Halt Policy
- On `BREAK ON ERROR`, the system marks the issue `blocked`, finalizes the report, and terminates (exit code 2).
- The system does not support auto-retry, skip, or in-process resume. Retry requires a manual rerun.

### FR-07 Interruption (Ctrl+C)
- On operator interrupt, the system shall forward the interrupt to the child process, wait up to 10 seconds (grace period), force terminate if still running, finalize the report, and exit (code 130).

### FR-08 Milestone Completion
- When all open issues in the milestone are processed with status `done`, the system shall close the milestone on GitHub (using Codex with a static prompt), finalize the report, and exit successfully (code 0).

## 3. Reporting Requirements

- Structured Markdown reports shall be stored globally outside target repos (e.g., `~/.codexor/reports/`).
- Filenames shall include project identifier, milestone identifier, and timestamp.
- **Run-Level Metadata:** `run_id`, `repo_full_name`, `milestone_name`, `run_status`, exit metrics, and duration.
- **Per-Issue Metadata:** issue key/number/title, timing, `final_status` (`done`/`blocked`/`halted`), `final_signal`, and blocker notes.
- Only one report file is written per run, updated incrementally.

## 4. Exit Codes & Run Status

| Exit Code | Run Status | Meaning |
|---|---|---|
| `0` | `completed` | All issues completed with `ALL DONE`, milestone closed. |
| `1` | `halted` | Unexpected internal error. |
| `2` | `blocked` | Run terminated by `BREAK ON ERROR`. |
| `3` | `halted` | Invalid or missing final signal. |
| `4` | `failed_config` | Configuration or validation failure. |
| `5` | `failed_dependency` | Dependency/auth/tooling failure (e.g., `gh`, `git` errors). |
| `130` | `interrupted` | Operator interrupt (Ctrl+C / SIGINT). |

Every fatal error shall emit one canonical diagnostic line:
`[codexor] level=error code=<error_code> run_status=<run_status> exit_code=<exit_code> detail="<message>"`