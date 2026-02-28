# Codex-Orchestrator v1 Architecture

## 1. Purpose and Scope

Codex-Orchestrator (`codexor`) automates milestone delivery for already planned GitHub issues.

It is an implementation orchestrator:
- fetches open issues from one milestone,
- runs them one-by-one in fresh Codex sessions,
- advances only on explicit completion signal.

It is not a planning tool:
- no milestone generation,
- no backlog strategy generation,
- no acceptance-criteria authoring from scratch.

## 2. System Context

The orchestrator coordinates four systems:
1. Local CLI process (`codexor`).
2. GitHub metadata and issue operations through `gh`.
3. Git repository workspace (local path or temporary clone).
4. Codex CLI subprocess for actual issue implementation.

User interaction occurs in one live terminal.
`codexor` prints orchestration markers, then streams Codex output directly while still parsing the final signal.

## 3. Technology and Runtime Decisions

1. Language/runtime: Python 3.11+.
2. Platform support: Windows-first, best-effort POSIX compatibility.
3. Process model: one Codex process per issue; no session reuse.
4. Handshake protocol:
   - success: `ALL DONE`
   - blocker/failure: `BREAK ON ERROR`
   - parsing rule: last non-empty output line
5. Resume/state recovery: not supported in v1.
6. CLI surface v1: one command with required flags only.

## 4. High-Level Component Architecture

## 4.1 CLI Entry
Module: `codexor.cli`

Responsibilities:
- parse `codexor run` flags,
- build immutable run config,
- execute orchestrator and return proper exit code.

## 4.2 Repo Resolver
Module: `codexor.repo`

Responsibilities:
- resolve `--repo` as local path or `owner/repo`,
- clone remote target to temp workspace,
- enforce clean worktree requirement,
- cleanup temp workspace only on successful full run.

## 4.3 GitHub Issue Provider
Module: `codexor.github`

Responsibilities:
- resolve `nameWithOwner` for local repos,
- load open milestone issues via `gh issue list`.

## 4.4 Issue Key Parser/Sorter
Module: `codexor.issue_key`

Responsibilities:
- parse key from title (`M<major>-<minorDigits>`),
- fail run if any issue key is missing,
- deterministic key ordering.

## 4.5 Prompt Template Engine
Module: `codexor.template`

Responsibilities:
- validate template file exists,
- validate placeholders against strict allow-list,
- render one issue-specific prompt.

## 4.6 Codex Session Runner
Module: `codexor.codex_runner`

Responsibilities:
- run fresh `codex --yolo --no-alt-screen` per issue,
- inject rendered prompt,
- stream live output to terminal,
- support user input passthrough,
- capture output tail and last non-empty line for signal detection.

## 4.7 Signal Parser
Module: `codexor.signals`

Responsibilities:
- normalize ANSI-laden terminal line,
- resolve to `ALL DONE`, `BREAK ON ERROR`, or `INVALID`.

## 4.8 Run Controller
Module: `codexor.orchestrator`

Responsibilities:
- state machine for sequential issue processing,
- enforce completion gates,
- stop on blocker/invalid signal,
- never skip to next issue on incomplete issue.

## 4.9 Report Writer
Module: `codexor.reporting`

Responsibilities:
- one Markdown report per run outside target repo,
- rewrite report incrementally after each processed issue,
- include per-issue timing/status/problem notes.

## 5. CLI Contract

v1 public command:

```bash
codexor run \
  --repo <owner/repo-or-local-path> \
  --milestone "<milestone-name>" \
  --prompt-template <path-to-snippet.md>
```

No additional required flags in v1.

## 6. Prompt Template Contract

Supported placeholders only:
- `{{ISSUE_KEY}}`
- `{{ISSUE_NUMBER}}`
- `{{ISSUE_TITLE}}`
- `{{MILESTONE_NAME}}`
- `{{REPO_FULL_NAME}}`

Template must end sessions with exact final line:
- `ALL DONE` when complete,
- `BREAK ON ERROR` when blocked.

Unsupported placeholders are a hard validation error.

## 7. Repository Resolution and Workspaces

## 7.1 Local Repository Mode
- `--repo` points to existing local directory.
- Directory must be a git working tree.
- Working tree must be clean (`git status --porcelain` empty).
- Repo full name resolved via `gh repo view`.

## 7.2 Remote Repository Mode
- `--repo` is `owner/repo`.
- Clone to: `~/.codexor/workspaces/<owner>__<repo>__<timestamp>`.
- Keep clone on halted/error run.
- Cleanup clone only when full run status is `completed`.

## 8. Issue Selection and Ordering

1. Query only open issues in selected milestone.
2. Parse issue keys from titles.
3. If any issue lacks parseable key, fail run before processing.
4. Sort by parsed key, not GitHub issue number.

Comparator design:
- compare major numeric part first,
- compare minor digit sequence deterministically.

Required ordering behavior:
- `M3-08 < M3-09`
- `M4-05 < M4-051 < M4-06`

## 9. Execution State Machine

States:
- `INIT`
- `PREPARING_RUN`
- `RUNNING_ISSUE`
- `ISSUE_DONE`
- `ISSUE_BLOCKED`
- `HALTED_INVALID_SIGNAL`
- `RUN_COMPLETED`

Transitions:
1. `RUNNING_ISSUE -> ISSUE_DONE` on `ALL DONE`.
2. `RUNNING_ISSUE -> ISSUE_BLOCKED` on `BREAK ON ERROR`.
3. `RUNNING_ISSUE -> HALTED_INVALID_SIGNAL` on any other final line.
4. `ISSUE_DONE -> RUNNING_ISSUE` for next sorted issue.
5. `RUN_COMPLETED` only if all issues ended `ALL DONE`.

## 10. Codex Terminal Interaction Model

Primary v1 strategy:
- single shared terminal,
- codexor streams Codex output in real time,
- codexor forwards user input to Codex process.

This keeps interaction possible when Codex explicitly waits for user decisions.

Planned fallback strategy (not default in v1):
- optional separate-terminal launch mode if shared-terminal passthrough is insufficient on specific environments.

## 11. Signal Handling Rules

Final signal source:
- last non-empty output line from Codex process.

Signal interpretation:
1. `ALL DONE`: mark issue `done`, continue.
2. `BREAK ON ERROR`: mark issue `blocked`, halt run.
3. anything else: mark issue `halted`, halt run.

No auto-retry or auto-resume in v1.

## 12. Reporting Architecture

Report storage:
- `~/.codexor/reports/`

File naming:
- `<repo-slug>__<milestone-slug>__<utc-timestamp>.md`

One file per run.

Required per-issue columns:
- issue key
- issue number
- issue title
- start time
- end time
- duration seconds
- status (`done`/`blocked`/`halted`)
- problems/notes

## 13. Error Handling and Failure Policy

Fail fast:
- invalid CLI args,
- missing prompt template,
- unsupported placeholders,
- non-clean local repo,
- missing parseable issue key,
- no open issues in milestone.

Halt-on-issue:
- `BREAK ON ERROR`,
- invalid/missing final signal,
- Codex process exits without acceptable signal.

Temporary clone retention:
- retain when halted/error for inspection.

## 14. Security and Operational Constraints

1. No secrets persisted in reports.
2. Strict subprocess argument lists (no shell interpolation required for core calls).
3. Reports remain outside target repositories to avoid polluting project history.
4. Orchestrator does not bypass repository policies; Codex enforces workflow via prompt instructions.

## 15. Public Interfaces and Core Types

Core run types:
- `RunConfig`
- `ResolvedRepo`
- `MilestoneIssue`
- `IssueKey`
- `CodexRunResult`
- `IssueRunResult`
- `RunReport`
- `FinalSignal`

Core module interfaces:
- `resolve_repo_target()`
- `load_open_milestone_issues()`
- `attach_and_sort_issues()`
- `load_prompt_template()` / `render_prompt()`
- `CodexRunner.run()`
- `parse_final_signal()`
- `ReportWriter.write()`
- `Orchestrator.run()`

## 16. Testing Strategy

## 16.1 Unit Tests
- issue key parsing and sort order.
- template placeholder validation/rendering.
- final signal parser.
- output-tail tracker line selection.
- report markdown renderer.

## 16.2 Integration Tests (next expansion)
- mock `gh` + `git` command layer.
- local vs remote repo flow.
- temporary clone retention/cleanup policy.
- halted-run behavior matrix.

## 16.3 End-to-End Harness (next expansion)
- stub codex command emitting:
  - `ALL DONE`,
  - `BREAK ON ERROR`,
  - invalid signal.

## 17. Implementation Milestones

1. Project scaffold and package entrypoint.
2. CLI command contract.
3. Repo resolution and clean-worktree enforcement.
4. GitHub milestone issue loading.
5. Issue-key parsing and deterministic ordering.
6. Prompt template validation and rendering.
7. Codex runner with live passthrough + tail capture.
8. Signal parser and run state machine.
9. Markdown reporting.
10. Unit test baseline.

## 18. Assumptions and Defaults

1. `gh`, `git`, and `codex` are installed and reachable in `PATH`.
2. Prompt template instructs full implementation lifecycle and required completion signals.
3. GitHub milestone/issue hygiene exists before automation run.
4. Naming convention uses parseable issue keys in titles.
5. Simplicity and deterministic control are prioritized over advanced recovery in v1.
