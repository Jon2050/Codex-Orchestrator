# Codex-Orchestrator Requirements

## 1. Purpose

Codex-Orchestrator shall automate end-to-end processing of GitHub issues by milestone, one issue at a time, with strict completion gating and fresh Codex sessions.

The system is implementation-focused:
- It executes already planned milestone work.
- It does not perform milestone or backlog planning.

## 2. Scope Boundary (Implementation, Not Planning)

The system shall:
- implement existing milestone issues,
- enforce delivery gates,
- orchestrate Codex + GitHub workflow.

The system shall not:
- create project strategy,
- generate milestone plans,
- invent missing acceptance criteria from nothing,
- replace product management planning.

## 3. Functional Requirements

### FR-01 Milestone Input
The system shall accept a milestone identifier/name and run only within that milestone.

### FR-02 Issue Source
The system shall load milestone issues from GitHub.

### FR-02a Repository Input Handling
The system shall accept either:
1. a local repository path, or
2. a GitHub `owner/repo` identifier.
If `owner/repo` is provided, the system shall clone the repository into a temporary working directory for the run.
If the run halts on blocker/error, that temporary directory shall be kept for manual inspection.
If the run fully succeeds, that temporary directory may be cleaned up.

### FR-03 Issue Eligibility
The system shall process only issues that are currently open in the selected milestone.

### FR-04 Ordering
The system shall process issues in deterministic order.
Default ordering: issue key naming order (not native GitHub issue number).
Example: `M3-08` < `M3-09`, `M4-05` < `M4-051` < `M4-06`.

### FR-05 Mandatory Prompt Template
The system shall require a prompt snippet file as input for runs.
If missing or invalid, run shall fail fast.

### FR-06 Prompt Rendering
The system shall render placeholders per issue before starting Codex.

### FR-07 Fresh Session Per Issue
The system shall start a brand-new Codex process for each issue.
No conversational context from previous issues shall be reused.

### FR-08 Low-Interaction Automation
The system shall minimize user interaction and proceed automatically unless blocked.

### FR-09 Hard Blocker Pause
On hard blocker, the system shall stop progression and wait for user instruction.

### FR-10 Completion Gate Enforcement
The system shall not continue to next issue unless Codex emits the required success signal.

### FR-10s Signal Protocol
The system shall require an explicit final signal from Codex at the end of each issue session:
1. `ALL DONE` for successful completion.
2. `BREAK ON ERROR` for blocked/error/manual-intervention state.
The signal is read from the last non-empty output line of the Codex process.
If no valid signal is present, the system shall halt.

### FR-10a Iterative Quality Loop
For each issue, the system shall enforce an iterative loop:
1. implement changes,
2. run tests/checks,
3. review against acceptance criteria and code quality expectations,
4. fix gaps,
5. repeat until all required conditions are satisfied.

### FR-10b Acceptance Criteria Enforcement
The system shall treat issue acceptance criteria as mandatory completion conditions.

### FR-11 Auto Merge
Codex shall perform merge/branch/issue completion actions as instructed by the prompt template.

### FR-12 Branch Deletion
Codex shall perform branch deletion after merge when required by repository policy.

### FR-13 Issue Closure
Codex shall close the issue when completion criteria are met.

### FR-14 CI Validation
Codex shall verify required CI/workflow checks are green when configured by the project and prompt.

### FR-15 Quota Handling
Quota/rate-limit behavior shall be handled by Codex inside the issue session.
If Codex exits without `ALL DONE`, the system shall halt.

### FR-16 External Reporting
The system shall store structured issue progress reports outside target repositories.
The required file output is a per-run issue list summary, not raw command logs.

### FR-16a Minimal CLI Surface
The first version shall expose only:
1. `codexor run`
2. required flags: `--repo`, `--milestone`, `--prompt-template`

### FR-16b No Mandatory Preflight Checks
The first version shall not require startup preflight checks (for example mandatory `gh auth status` or `codex --version` checks).

### FR-17 Multi-Repo Reuse
The system shall be usable for different repositories without repo-local implementation.

## 4. Prompt Snippet Contract

A run requires `--prompt-template <file>`.

The template should include placeholders:
- `{{ISSUE_KEY}}`
- `{{ISSUE_NUMBER}}`
- `{{ISSUE_TITLE}}`
- `{{MILESTONE_NAME}}`
- `{{REPO_FULL_NAME}}`
No additional placeholders are supported in v1.

The template shall instruct Codex to load project context from repository docs/issues and execute implementation steps with verification.
The template shall also require Codex to emit a final handshake line: `ALL DONE` or `BREAK ON ERROR`.

## 5. Context Delivery Requirements

### 5.1 Orchestrator-Provided Context
The orchestrator shall provide issue and run metadata to the rendered prompt.

### 5.2 Codex-Resolved Context
Codex shall resolve project-specific implementation context from:
- repository files/docs,
- issue details,
- linked PR/CI information,
- quality gate definitions in the project.
If issue information is insufficient, Codex shall ask the user for input and use `BREAK ON ERROR` when it cannot continue.

### 5.3 Isolation Rule
Each issue session shall be isolated from previous issue conversation state.

## 6. Target Project Prerequisites

Target project must provide:
1. GitHub milestones.
2. Milestone issues.
3. Issue workflow suitable for implementation execution.
4. PR-based integration to `main`.
5. Accessible `gh` context and permissions.
6. Available `codex` CLI runtime.

Recommended:
1. Stable issue naming, e.g. `M<k>-<n>`.
2. Clear issue-to-PR linkage.
3. CI/CD checks available for stronger automated quality gates.
4. Branch/PR delivery details (for example one issue branch and one PR per issue) defined in the prompt snippet.

## 7. Completion Gate (All Mandatory)

An issue is complete only when Codex emits `ALL DONE` after executing project-defined completion steps.

If Codex emits `BREAK ON ERROR`, the issue remains incomplete and next issue shall not start.

## 8. Blocker Policy

When blocked:
1. Mark current issue blocked in runtime status and report output.
2. Persist blocker reason/details in report.
3. Halt automatic progression.
4. Wait for explicit user action.
5. Do not skip by default.

## 9. Quota and Rate-Limit Policy

Quota/rate-limit handling is delegated to Codex during the issue session.
If Codex exits without `ALL DONE`, the orchestrator halts and does not auto-retry.

## 10. Reporting Requirements

### 10.1 Storage Location
Reports shall be stored globally outside target repos.

### 10.2 Naming Rule
Run path/name shall include:
- project identifier,
- milestone identifier,
- timestamp.

### 10.3 Per-Issue Report Fields
At minimum:
- issue key/number/title,
- start time,
- finish time,
- duration,
- final status (`done`/`blocked`),
- blocker reason when applicable,
- difficulty flags (quota, CI failure, merge conflict, manual interaction).

### 10.4 Output Shape
The run output file shall be a Markdown file with a clean table for processed issues and timing/status/problem fields.
Detailed terminal logs are optional and not required as persisted report artifacts.
Exactly one report file shall be written per run.

## 11. Non-Functional Requirements

1. Keep implementation lightweight and pragmatic.
2. Be robust for long-running milestone automation sessions.
3. Provide readable summaries and clear live terminal progress.
4. Avoid silent skips of incomplete issues.
5. Remain repository-agnostic.

## 12. Acceptance Scenarios

### AS-01 Happy Path
Given valid milestone with actionable issues, system processes all sequentially and enforces full gate per issue.

### AS-02 Mandatory User Input
Given Codex requires concrete user input, system pauses and waits at current issue.

### AS-03 CI Failure
Given configured required checks fail, system does not advance.

### AS-04 Quota Exhausted
Given quota/rate limit is exhausted, Codex handles it inside the session; if it exits without `ALL DONE`, system halts.

### AS-05 Unresolvable Issue
Given issue cannot be completed, system records blocker report and waits for instruction.

### AS-06 Review or Acceptance Criteria Gap
Given tests/checks are green but acceptance criteria or review expectations are not fully met, system requires another fix cycle and does not advance.

## 13. Defaults and Assumptions

1. Default Codex baseline command: `codex --yolo --no-alt-screen`.
2. Default issue order: issue key naming order.
3. Default blocker behavior: stop and wait.
4. One milestone per run.
5. No resume support by default; runs are intentionally simple and session-driven.
6. If Codex exits without a valid final signal, run halts and requires manual restart.
