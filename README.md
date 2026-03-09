# Codex-Orchestrator

Codex-Orchestrator automates milestone delivery across GitHub issues by running Codex issue-by-issue in a strict, completion-gated sequence.

## Scope

This tool implements already planned milestone issues. It runs those issues sequentially, one issue at a time, with a fresh isolated Codex process per issue.

It does **not** plan projects, design milestones, write backlog strategy, or replace product planning.

## Required Project Conditions

1. Hosted on GitHub with `gh` CLI access authenticated.
2. Milestones and implementation-ready issues exist.
3. Issues have stable keys matching `\bM(?P<major>\d+)-(?P<minor>\d+)\b` (e.g., `M2-01`). Duplicate keys are not allowed.
4. A PR workflow exists (e.g., issue branch -> PR -> merge).
5. `codex` CLI is installed.

## Core Workflow

1. Run `codexor run` inside the target repository with a milestone identifier and a prompt template.
2. The orchestrator loads all open issues for the milestone, validates the environment, and prints the ordered list of issues with their numbers and titles.
3. Issues are processed sequentially based on their issue key.
4. For each issue, the template is rendered and a fresh `codex` session starts (`codex --yolo --no-alt-screen`).
5. Codex must end its output with exactly `ALL DONE` (success) or `BREAK ON ERROR` (blocked).
6. The orchestrator pauses on a blocker or halts on an invalid signal. You can safely abort a run using Ctrl+C, which grants a 10-second grace period for the Codex process to terminate cleanly.
7. Once all open issues are processed with status `done`, the orchestrator uses a static prompt to close the milestone on GitHub.

## Prompt Snippet Contract

A prompt snippet file is mandatory (`--prompt-template <path-to-snippet.md>`). This snippet tells Codex how to execute the implementation and when to emit the required signals.

### Placeholders
The orchestrator supports exactly these placeholders:
- `{{ISSUE_KEY}}`
- `{{ISSUE_NUMBER}}`
- `{{ISSUE_TITLE}}`
- `{{ISSUE_BODY}}`
- `{{MILESTONE_NAME}}`
- `{{REPO_FULL_NAME}}`

*Note: Literal `{` or `}` in your template must be escaped as `{{` and `}}` if they look like placeholders, specifically literal `{{` must be escaped as `{{{{` and `}}` as `}}}}`.*

### Prompt Snippet Example

```md
# Task Prompt Snippet (Example)

Task: Implement issue `{{ISSUE_KEY}}` (GitHub #{{ISSUE_NUMBER}}) for milestone `{{MILESTONE_NAME}}` in `{{REPO_FULL_NAME}}`.

Issue Description:
{{ISSUE_BODY}}

Rules:
- Work only in this repository.
- Implement only what is required for this issue.
- Keep changes minimal but complete.

Execution:
1) Load project context from README, architecture docs, backlog docs, and the GitHub issue.
2) Extract acceptance criteria and dependencies.
3) Implement end-to-end with tests.
4) Run required local checks.
5) Review changes against acceptance criteria. If failing, fix and repeat.
6) Open PR, ensure CI is green, merge to main, and delete branch.
7) Close issue.

End with exactly one of these lines:
- `ALL DONE` when fully completed.
- `BREAK ON ERROR` if user input is needed or you are permanently stuck.
```

## Getting Started

### 1. Install

```bash
python -m pip install -e .
```

### 2. Run

Run from inside the checked-out target repository:

```bash
codexor run \
  --milestone "<milestone-number-like-M4>" \
  --prompt-template prompt.md
```

### 3. Reporting
Structured progress reports are written globally to `~/.codexor/reports/`. They track timing, status (`done`/`blocked`/`halted`), and summaries per issue.

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Requirements](docs/REQUIREMENTS.md)