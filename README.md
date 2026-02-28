# Codex-Orchestrator

Codex-Orchestrator automates milestone delivery across GitHub issues by running Codex issue-by-issue in a strict, completion-gated sequence.

This tool is intentionally focused on execution:
- It implements already planned milestone issues.
- It does not plan projects, design milestones, or create issue scopes.

## What This Tool Is For

Use Codex-Orchestrator when your project already has:
- defined milestones in GitHub,
- existing milestone issues with actionable acceptance criteria,
- a PR workflow,
- a prompt snippet that tells Codex how to execute implementation.

Codex-Orchestrator then runs those issues sequentially, one issue at a time, with a fresh Codex process per issue.

## What This Tool Is Not For

Codex-Orchestrator is not a planning system.

It does not:
- generate milestones,
- write backlog strategy,
- design issue acceptance criteria from scratch,
- replace product planning.

It executes implementation work for an already planned milestone backlog.

## Required Project Conditions

A target project should meet these conditions:
1. Hosted on GitHub.
2. Milestones exist.
3. Issues for that milestone exist and are implementation-ready.
4. PR workflow exists (issue branch -> PR -> merge).
5. `gh` CLI access is available and authenticated.
6. `codex` CLI is installed.

Recommended conventions:
1. Milestone naming is stable, e.g. `M2 - Website Integration + Early Deploy`.
2. Issue keys use a stable pattern, e.g. `M2-01`, `M2-02`.
3. CI/CD quality checks are available and used as completion gates when possible.
4. Delivery flow details (for example one dedicated branch and one PR per issue) are defined in the prompt snippet.

## Core Workflow

1. Start run with repository, milestone, and prompt template path.
   - `--repo` accepts either a local path or `owner/repo`.
   - For `owner/repo`, the orchestrator clones to a temporary working directory for the run.
   - If the run halts with an error/blocker, keep the temp directory for inspection.
   - If the full run finishes successfully, cleanup the temp directory.
2. Load all open issues in that milestone.
3. Process issues in deterministic order by issue key naming (not native GitHub number).
   - Example ordering: `M3-08` < `M3-09`, `M4-05` < `M4-051` < `M4-06`.
4. For each issue, render prompt from template and start a fresh `codex --yolo --no-alt-screen` session.
5. Continue only when Codex ends with the success signal `ALL DONE`.
6. If Codex ends with `BREAK ON ERROR`, stop and wait for user interaction.
7. If Codex exits without one of the required final signals, stop immediately.

## Codex-Orchestrator Handshake Signals

To keep orchestration simple and deterministic, the prompt snippet must require Codex to end with one of these exact final lines:
- `ALL DONE` when the issue is fully completed (including tests/review/acceptance criteria and repository delivery flow).
- `BREAK ON ERROR` when it cannot complete the issue after multiple attempts or when user input is required to proceed.

The orchestrator uses these signals to decide whether to advance or pause.
Signal parsing rule:
- The last non-empty output line from the Codex process is treated as the final signal.
- If it is not exactly `ALL DONE` or `BREAK ON ERROR`, the run halts.

## Mandatory Prompt Snippet File

A prompt snippet file must exist and be provided for each run.

Without a valid prompt template file, the run must fail fast.

Typical input:
- `--prompt-template <path-to-snippet.md>`

### Supported Placeholder Variables

The orchestrator renders issue-specific values into the snippet:
- `{{ISSUE_KEY}}`
- `{{ISSUE_NUMBER}}`
- `{{ISSUE_TITLE}}`
- `{{MILESTONE_NAME}}`
- `{{REPO_FULL_NAME}}`
Only these placeholders are supported in v1.

## Prompt Snippet Example

```md
# Task Prompt Snippet (Example)

Task: Implement issue `{{ISSUE_KEY}}` (GitHub #{{ISSUE_NUMBER}}) for milestone `{{MILESTONE_NAME}}` in `{{REPO_FULL_NAME}}`.

Rules:
- Work only in this repository.
- Implement only what is required for this issue.
- If ambiguous, infer from project docs and state assumptions.
- Ask questions only for true blockers.
- Keep changes minimal but complete.

Execution:
1) Load project context from README, architecture docs, backlog docs, and the GitHub issue.
2) Extract acceptance criteria and dependencies.
3) Plan concrete file-level changes mapped to acceptance criteria.
4) Implement end-to-end with tests.
5) Run required local checks.
6) Review changes against acceptance criteria and code review best practices.
7) If checks fail, review fails, or any acceptance criterion is not met: fix and repeat steps 4-6 until all pass.
8) Open/update PR, push changes, and link issue.
9) Ensure required CI checks are green.
10) Merge PR to main and delete branch.
11) Close issue and update any required backlog status.
12) Report changed files, checks, CI status, acceptance criteria checklist, assumptions.

QA / Quality / Repo Rules:
- Quality gate must be green before completion (format, lint, typecheck, tests, build; plus e2e when relevant).
- Acceptance criteria are mandatory completion conditions.
- Do not change unrelated files; keep scope tight to this issue.
- Follow repository contribution rules and branch/PR policy defined by project docs.
- If blocked by missing information, auth issues, merge conflicts, or required manual decision, ask the user what to do and end with `BREAK ON ERROR`.

Completion Signal:
- If everything is fully complete and all criteria are satisfied, end with `ALL DONE`.
- If not possible after multiple attempts, end with `BREAK ON ERROR`.

Stop and wait if blocked.
```

## How Context Delivery Works

Context delivery is split into two parts:

1. Orchestrator-delivered context (structured metadata)
- Issue key/number/title
- milestone name
- repository identifier
- optional run metadata

2. Codex self-loaded context (inside issue session)
- repository files and docs
- architecture/backlog sources
- current issue and linked PR information
- test and CI expectations defined in project docs

This keeps the orchestrator generic and keeps project intelligence inside the prompt snippet + repo.
If issue details are insufficient, Codex must ask the user for input and use `BREAK ON ERROR` when it cannot continue.

## Session Isolation

Each issue starts a brand-new Codex process.

Why:
- avoids cross-issue context junk,
- reduces stale assumptions,
- keeps execution issue-scoped and easier to monitor in a live terminal.

No conversational state is reused across issues, and there is no resume/state-recovery mechanism by default.

## Completion Gate (Must Pass Before Next Issue)

The next issue must not start until Codex emits `ALL DONE`.

In this simplified model, Codex is responsible for completing and validating the delivery flow inside the issue session.
If Codex cannot complete the issue, it must emit `BREAK ON ERROR`, and the orchestrator pauses.
If Codex exits without a valid signal, the orchestrator halts and waits for manual decision.

## Blockers and User Interaction

The run should require as little user interaction as possible.

It pauses only on hard blockers, e.g.:
- Codex needs concrete user input,
- unresolved CI failure,
- merge conflict,
- permission/auth gap,
- missing required artifact/state for completion.

In blocker state, the orchestrator waits for user instruction and does not skip the issue by default.

## Quota / Rate-Limit Behavior

Quota/rate-limit handling is intentionally simple:
- Codex should decide when to continue waiting vs. ask for user intervention.
- The orchestrator does not auto-retry based on log parsing.
- If Codex does not end with `ALL DONE`, the orchestrator halts.

## Reporting

The orchestrator writes only structured progress files outside target repos (global location under user home).
It does not rely on persistent command log files as a required output.

Each run records a simple issue list in Markdown table format:
- issue key/number/title
- start time
- end time
- duration
- status (`done`/`blocked`)
- notable difficulties/problems

Run naming includes project + milestone + timestamp.
Exactly one report file is written per run.

## Conceptual Usage

```bash
codexor run \
  --repo <owner/repo-or-local-path> \
  --milestone "<milestone-name>" \
  --prompt-template <path-to-snippet.md>
```

Minimal CLI scope:
- `codexor run` command only
- Required flags only: `--repo`, `--milestone`, `--prompt-template`
- No mandatory preflight checks in v1 (for example no required `gh auth status` / `codex --version` check).

## Scope Summary

Codex-Orchestrator is a thin orchestration layer around `codex` and `gh` for milestone execution quality.

It enforces sequencing and completion discipline for implementation.
It is not a planning assistant.

## Current Implementation (v1)

The repository now includes a working Python CLI implementation:
- package: `codexor`
- command: `codexor run`
- architecture spec: `docs/ARCHITECTURE.md`

Installation for local usage:

```bash
python -m pip install -e .
```

Run:

```bash
codexor run \
  --repo <owner/repo-or-local-path> \
  --milestone "<milestone-name>" \
  --prompt-template <path-to-snippet.md>
```
