# PR Test Runner — Design Spec

**Date:** 2026-04-21
**Status:** Approved

---

## Overview

A Python CLI tool (`pr-test-runner`) that detects test files changed in the current branch's open GitHub PR and runs each one sequentially, removing the need to manually find and execute them.

Scope: Django projects. Built to be distributable via pip and extendable later.

---

## Architecture

Five focused modules, each with a single responsibility:

### `cli.py`
Entry point. Parses arguments (`--dry-run`), orchestrates calls to the other modules in order, and handles top-level error display.

### `git.py`
Detects the current git branch, the repo root (via `git rev-parse --show-toplevel`), and parses the GitHub remote URL to extract `owner/repo`. Uses `subprocess` to call git directly.

### `github.py`
Handles GitHub authentication and API calls.
- Auth: checks `GITHUB_TOKEN` env var first, falls back to `gh auth token` (if `gh` CLI is installed), fails with a clear message if neither is available
- Fetches the open PR for the current branch via GitHub REST API
- Returns the list of changed files in that PR

### `resolver.py`
Filters and transforms changed file paths into runnable test modules.
- Filters to files matching `*/tests/test_*.py` or `*/tests/*.py`
- Converts file path to Django dot-notation: strips `.py`, replaces `/` with `.`
- Example: `accounts/tests/test_models.py` → `accounts.tests.test_models`

### `runner.py`
Executes tests sequentially.
- Reads `.pr-test-runner.yml` from the repo root
- Substitutes `{module}` into the command template for each resolved test module
- Runs each command via `subprocess`, streaming output live to the terminal
- Tracks exit codes for the final summary

---

## Configuration

A `.pr-test-runner.yml` file in the git repo root (located via `git rev-parse --show-toplevel`, so the tool works from any subdirectory):

```yaml
command: "docker-compose exec django python manage.py test {module}"
```

`{module}` is replaced with the dot-notation test path at runtime.

---

## CLI Interface

```bash
pr-test-runner [--dry-run]
```

**Flags:**
- `--dry-run` — prints the commands that would be run without executing them

**No required arguments.** The tool is run from anywhere inside the repo.

---

## Execution Flow

1. Read `.pr-test-runner.yml` from repo root
2. Detect current git branch and `owner/repo` from remote URL
3. Authenticate with GitHub
4. Find open PR for current branch
5. Fetch changed files from PR
6. Filter and resolve to Django test module paths
7. If none found, print info message and exit cleanly
8. For each module: print command, run it, stream output
9. Print final summary: total ran, passed, failed (by exit code)

---

## Error Handling

| Situation | Behavior |
|---|---|
| No `.pr-test-runner.yml` found | Error: "No config file found. Create a `.pr-test-runner.yml` in your repo root." |
| Not inside a git repo | Error: "Not a git repository." |
| No GitHub remote found | Error: "Could not detect GitHub remote." |
| No auth token available | Error: "No GitHub token found. Set `GITHUB_TOKEN` or run `gh auth login`." |
| No open PR for current branch | Error: "No open PR found for branch `{branch}`." |
| No test files in PR diff | Info: "No test files found in PR. Nothing to run." |
| Test command exits non-zero | Print failure, continue remaining tests, reflect in summary |
| Config missing `{module}` placeholder | Warning: "Command template has no `{module}` placeholder." |

---

## Dependencies

- `httpx` — GitHub REST API calls
- `PyYAML` — config file parsing
- Standard library only beyond that (`subprocess`, `os`, `sys`, `pathlib`)

---

## Package Structure

```
pr-test-runner/
├── pr_test_runner/
│   ├── __init__.py
│   ├── cli.py          # entry point, argument parsing
│   ├── git.py          # branch and remote detection
│   ├── github.py       # auth and API calls
│   ├── resolver.py     # file path → test module mapping
│   └── runner.py       # config loading and command execution
├── pyproject.toml
└── README.md
```

---

## Out of Scope (for now)

- Non-Django projects
- Parallel test execution
- PR number specified manually
- Auto-detection of test framework
