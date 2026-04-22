# PR Test Runner Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a pip-installable Python CLI tool that finds test files changed in the current branch's open GitHub PR and runs each one sequentially using a per-project config file.

**Architecture:** Five focused modules — `git.py` (branch/remote detection), `github.py` (auth + API), `resolver.py` (file → Django module path), `runner.py` (config + execution), `cli.py` (entry point). Auth checks `GITHUB_TOKEN` env var first, falls back to `gh auth token`. Test files are filtered to `*/tests/test_*.py` and converted to dot-notation before being substituted into the configured command template.

**Tech Stack:** Python 3.11+, httpx (GitHub REST API), PyYAML (config parsing), pytest + unittest.mock (tests), hatchling (build backend)

---

## File Map

| File | Responsibility |
|---|---|
| `pyproject.toml` | Package metadata, dependencies, entry point |
| `pr_test_runner/__init__.py` | Empty package marker |
| `pr_test_runner/git.py` | Detect branch, repo root, owner/repo from remote |
| `pr_test_runner/github.py` | GitHub auth and REST API calls |
| `pr_test_runner/resolver.py` | Filter test files, convert path to Django dot-notation |
| `pr_test_runner/runner.py` | Load config, execute commands sequentially |
| `pr_test_runner/cli.py` | Argument parsing, orchestration, error display |
| `tests/test_git.py` | Unit tests for git.py |
| `tests/test_github.py` | Unit tests for github.py |
| `tests/test_resolver.py` | Unit tests for resolver.py |
| `tests/test_runner.py` | Unit tests for runner.py |
| `tests/test_cli.py` | Integration tests for cli.py |

---

### Task 1: Project Scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `pr_test_runner/__init__.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: Create pyproject.toml**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "pr-test-runner"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "httpx>=0.24.0",
    "PyYAML>=6.0",
]

[project.optional-dependencies]
dev = ["pytest>=7.0"]

[project.scripts]
pr-test-runner = "pr_test_runner.cli:main"

[tool.hatch.build.targets.wheel]
packages = ["pr_test_runner"]
```

- [ ] **Step 2: Create package and test directories**

```bash
mkdir -p pr_test_runner tests
touch pr_test_runner/__init__.py tests/__init__.py
```

- [ ] **Step 3: Install package in editable mode with dev dependencies**

```bash
pip install -e ".[dev]"
```

Expected output ends with: `Successfully installed pr-test-runner-0.1.0`

- [ ] **Step 4: Verify entry point is registered**

```bash
pr-test-runner --help
```

Expected: error about missing module `pr_test_runner.cli` (entry point wired up, module not yet created — that's fine).

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml pr_test_runner/__init__.py tests/__init__.py
git commit -m "chore: scaffold pr-test-runner package"
```

---

### Task 2: git.py — Branch, Repo Root, and Remote Detection

**Files:**
- Create: `pr_test_runner/git.py`
- Create: `tests/test_git.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_git.py`:

```python
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
from pr_test_runner.git import get_repo_root, get_current_branch, get_github_remote, GitError


def make_proc(stdout="", returncode=0):
    m = MagicMock()
    m.stdout = stdout
    m.returncode = returncode
    return m


def test_get_repo_root_returns_path():
    with patch("subprocess.run", return_value=make_proc("/home/user/myrepo\n")) as mock_run:
        result = get_repo_root()
    assert result == Path("/home/user/myrepo")
    mock_run.assert_called_once_with(
        ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True
    )


def test_get_repo_root_raises_when_not_git_repo():
    with patch("subprocess.run", return_value=make_proc(returncode=128)):
        with pytest.raises(GitError, match="Not a git repository"):
            get_repo_root()


def test_get_current_branch_returns_branch_name():
    with patch("subprocess.run", return_value=make_proc("feature/my-branch\n")):
        assert get_current_branch() == "feature/my-branch"


def test_get_current_branch_raises_when_not_git_repo():
    with patch("subprocess.run", return_value=make_proc(returncode=128)):
        with pytest.raises(GitError, match="Not a git repository"):
            get_current_branch()


def test_get_github_remote_parses_https_url():
    with patch("subprocess.run", return_value=make_proc("https://github.com/myorg/myrepo.git\n")):
        owner, repo = get_github_remote()
    assert owner == "myorg"
    assert repo == "myrepo"


def test_get_github_remote_parses_ssh_url():
    with patch("subprocess.run", return_value=make_proc("git@github.com:myorg/myrepo.git\n")):
        owner, repo = get_github_remote()
    assert owner == "myorg"
    assert repo == "myrepo"


def test_get_github_remote_raises_when_no_remote():
    with patch("subprocess.run", return_value=make_proc(returncode=2)):
        with pytest.raises(GitError, match="Could not detect GitHub remote"):
            get_github_remote()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_git.py -v
```

Expected: `ImportError: cannot import name 'get_repo_root' from 'pr_test_runner.git'` (module does not exist yet).

- [ ] **Step 3: Create pr_test_runner/git.py**

```python
import re
import subprocess
from pathlib import Path


class GitError(Exception):
    pass


def get_repo_root() -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True
    )
    if result.returncode != 0:
        raise GitError("Not a git repository.")
    return Path(result.stdout.strip())


def get_current_branch() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True
    )
    if result.returncode != 0:
        raise GitError("Not a git repository.")
    return result.stdout.strip()


def get_github_remote() -> tuple[str, str]:
    result = subprocess.run(
        ["git", "remote", "get-url", "origin"], capture_output=True, text=True
    )
    if result.returncode != 0:
        raise GitError("Could not detect GitHub remote.")
    url = result.stdout.strip()
    match = re.match(r"https://github\.com/([^/]+)/([^/]+?)(?:\.git)?$", url)
    if not match:
        match = re.match(r"git@github\.com:([^/]+)/([^/]+?)(?:\.git)?$", url)
    if not match:
        raise GitError("Could not detect GitHub remote.")
    return match.group(1), match.group(2)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_git.py -v
```

Expected: 7 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add pr_test_runner/git.py tests/test_git.py
git commit -m "feat: add git branch and remote detection"
```

---

### Task 3: resolver.py — Filter Test Files and Convert to Module Paths

**Files:**
- Create: `pr_test_runner/resolver.py`
- Create: `tests/test_resolver.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_resolver.py`:

```python
from pr_test_runner.resolver import filter_test_files, path_to_module


def test_filter_keeps_nested_test_files():
    files = ["accounts/tests/test_models.py", "accounts/tests/test_views.py"]
    assert filter_test_files(files) == files


def test_filter_excludes_non_test_python_files():
    files = ["accounts/models.py", "accounts/views.py", "accounts/tests/test_models.py"]
    assert filter_test_files(files) == ["accounts/tests/test_models.py"]


def test_filter_excludes_test_files_not_under_tests_dir():
    files = ["test_something.py", "accounts/test_models.py"]
    assert filter_test_files(files) == []


def test_filter_excludes_init_files_in_tests_dir():
    files = ["accounts/tests/__init__.py", "accounts/tests/test_models.py"]
    assert filter_test_files(files) == ["accounts/tests/test_models.py"]


def test_path_to_module_converts_slashes_and_strips_extension():
    assert path_to_module("accounts/tests/test_models.py") == "accounts.tests.test_models"


def test_path_to_module_handles_deep_nesting():
    assert path_to_module("apps/billing/tests/test_invoices.py") == "apps.billing.tests.test_invoices"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_resolver.py -v
```

Expected: `ImportError: cannot import name 'filter_test_files' from 'pr_test_runner.resolver'`.

- [ ] **Step 3: Create pr_test_runner/resolver.py**

```python
import fnmatch


def filter_test_files(files: list[str]) -> list[str]:
    return [f for f in files if fnmatch.fnmatch(f, "*/tests/test_*.py")]


def path_to_module(file_path: str) -> str:
    return file_path.replace("/", ".").removesuffix(".py")
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_resolver.py -v
```

Expected: 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add pr_test_runner/resolver.py tests/test_resolver.py
git commit -m "feat: add test file filter and module path resolver"
```

---

### Task 4: github.py — Auth and PR File Fetching

**Files:**
- Create: `pr_test_runner/github.py`
- Create: `tests/test_github.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_github.py`:

```python
import pytest
from unittest.mock import patch, MagicMock
from pr_test_runner.github import get_token, get_pr_files, GitHubError


def test_get_token_reads_from_env(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "mytoken123")
    assert get_token() == "mytoken123"


def test_get_token_falls_back_to_gh_cli(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.stdout = "ghp_abc123\n"
    with patch("subprocess.run", return_value=mock_proc):
        assert get_token() == "ghp_abc123"


def test_get_token_raises_when_no_auth_available(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    mock_proc = MagicMock()
    mock_proc.returncode = 1
    mock_proc.stdout = ""
    with patch("subprocess.run", return_value=mock_proc):
        with pytest.raises(GitHubError, match="No GitHub token found"):
            get_token()


def make_response(json_data, status_code=200):
    m = MagicMock()
    m.json.return_value = json_data
    m.status_code = status_code
    m.raise_for_status = MagicMock()
    return m


def test_get_pr_files_returns_list_of_filenames():
    pr_list = [{"number": 42}]
    pr_files = [
        {"filename": "accounts/tests/test_models.py"},
        {"filename": "accounts/models.py"},
    ]
    with patch("httpx.get", side_effect=[make_response(pr_list), make_response(pr_files)]):
        result = get_pr_files("myorg", "myrepo", "feature/branch", "token123")
    assert result == ["accounts/tests/test_models.py", "accounts/models.py"]


def test_get_pr_files_raises_when_no_open_pr():
    with patch("httpx.get", return_value=make_response([])):
        with pytest.raises(GitHubError, match="No open PR found for branch"):
            get_pr_files("myorg", "myrepo", "feature/branch", "token123")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_github.py -v
```

Expected: `ImportError: cannot import name 'get_token' from 'pr_test_runner.github'`.

- [ ] **Step 3: Create pr_test_runner/github.py**

```python
import os
import subprocess
import httpx


class GitHubError(Exception):
    pass


def get_token() -> str:
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        return token
    result = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True)
    if result.returncode == 0 and result.stdout.strip():
        return result.stdout.strip()
    raise GitHubError(
        "No GitHub token found. Set GITHUB_TOKEN or run `gh auth login`."
    )


def get_pr_files(owner: str, repo: str, branch: str, token: str) -> list[str]:
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }
    response = httpx.get(
        f"https://api.github.com/repos/{owner}/{repo}/pulls",
        params={"state": "open", "head": f"{owner}:{branch}"},
        headers=headers,
    )
    response.raise_for_status()
    prs = response.json()
    if not prs:
        raise GitHubError(f"No open PR found for branch `{branch}`.")
    pr_number = prs[0]["number"]
    files_response = httpx.get(
        f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/files",
        headers=headers,
    )
    files_response.raise_for_status()
    return [f["filename"] for f in files_response.json()]
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_github.py -v
```

Expected: 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add pr_test_runner/github.py tests/test_github.py
git commit -m "feat: add GitHub auth and PR file fetching"
```

---

### Task 5: runner.py — Config Loading and Sequential Command Execution

**Files:**
- Create: `pr_test_runner/runner.py`
- Create: `tests/test_runner.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_runner.py`:

```python
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, call
from pr_test_runner.runner import load_config, run_tests, ConfigError


def test_load_config_returns_command(tmp_path):
    (tmp_path / ".pr-test-runner.yml").write_text(
        'command: "docker-compose exec django python manage.py test {module}"\n'
    )
    config = load_config(tmp_path)
    assert config["command"] == "docker-compose exec django python manage.py test {module}"


def test_load_config_raises_when_file_missing(tmp_path):
    with pytest.raises(ConfigError, match="No config file found"):
        load_config(tmp_path)


def test_load_config_warns_when_placeholder_missing(tmp_path, capsys):
    (tmp_path / ".pr-test-runner.yml").write_text('command: "manage.py test"\n')
    load_config(tmp_path)
    assert "no `{module}` placeholder" in capsys.readouterr().out


def test_run_tests_dry_run_prints_commands_without_subprocess(capsys):
    with patch("subprocess.run") as mock_run:
        results = run_tests(
            ["accounts.tests.test_models"], "manage.py test {module}", dry_run=True
        )
    mock_run.assert_not_called()
    assert "manage.py test accounts.tests.test_models" in capsys.readouterr().out
    assert results == [("accounts.tests.test_models", 0)]


def test_run_tests_executes_each_module_sequentially():
    mock_proc = MagicMock(returncode=0)
    with patch("subprocess.run", return_value=mock_proc) as mock_run:
        results = run_tests(
            ["accounts.tests.test_models", "accounts.tests.test_views"],
            "manage.py test {module}",
        )
    assert mock_run.call_args_list == [
        call("manage.py test accounts.tests.test_models", shell=True),
        call("manage.py test accounts.tests.test_views", shell=True),
    ]
    assert results == [
        ("accounts.tests.test_models", 0),
        ("accounts.tests.test_views", 0),
    ]


def test_run_tests_continues_after_failure():
    procs = [MagicMock(returncode=0), MagicMock(returncode=1), MagicMock(returncode=0)]
    with patch("subprocess.run", side_effect=procs):
        results = run_tests(
            ["a.tests.test_1", "a.tests.test_2", "a.tests.test_3"],
            "manage.py test {module}",
        )
    assert len(results) == 3
    assert results[1] == ("a.tests.test_2", 1)
    assert results[2] == ("a.tests.test_3", 0)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_runner.py -v
```

Expected: `ImportError: cannot import name 'load_config' from 'pr_test_runner.runner'`.

- [ ] **Step 3: Create pr_test_runner/runner.py**

```python
import subprocess
from pathlib import Path
import yaml


class ConfigError(Exception):
    pass


def load_config(repo_root: Path) -> dict:
    config_path = repo_root / ".pr-test-runner.yml"
    if not config_path.exists():
        raise ConfigError(
            "No config file found. Create a `.pr-test-runner.yml` in your repo root."
        )
    config = yaml.safe_load(config_path.read_text())
    if "{module}" not in config.get("command", ""):
        print("Warning: Command template has no `{module}` placeholder.")
    return config


def run_tests(
    modules: list[str], command_template: str, dry_run: bool = False
) -> list[tuple[str, int]]:
    results = []
    for module in modules:
        command = command_template.replace("{module}", module)
        print(f"\n>>> Running: {command}")
        if dry_run:
            results.append((module, 0))
            continue
        proc = subprocess.run(command, shell=True)
        results.append((module, proc.returncode))
    return results
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_runner.py -v
```

Expected: 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add pr_test_runner/runner.py tests/test_runner.py
git commit -m "feat: add config loading and sequential test runner"
```

---

### Task 6: cli.py — Entry Point and Orchestration

**Files:**
- Create: `pr_test_runner/cli.py`
- Create: `tests/test_cli.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_cli.py`:

```python
import pytest
from unittest.mock import patch, MagicMock
from pr_test_runner.cli import main
from pr_test_runner.git import GitError
from pr_test_runner.github import GitHubError
from pr_test_runner.runner import ConfigError


def make_proc(returncode=0):
    m = MagicMock()
    m.returncode = returncode
    return m


@pytest.fixture
def base_patches(tmp_path):
    (tmp_path / ".pr-test-runner.yml").write_text('command: "manage.py test {module}"\n')
    with (
        patch("pr_test_runner.cli.get_repo_root", return_value=tmp_path),
        patch("pr_test_runner.cli.get_current_branch", return_value="feature/my-branch"),
        patch("pr_test_runner.cli.get_github_remote", return_value=("myorg", "myrepo")),
        patch("pr_test_runner.cli.get_token", return_value="token123"),
        patch("pr_test_runner.cli.get_pr_files", return_value=["accounts/tests/test_models.py"]),
    ):
        yield tmp_path


def test_cli_runs_tests_and_prints_summary(base_patches, capsys):
    with (
        patch("subprocess.run", return_value=make_proc(0)),
        patch("sys.argv", ["pr-test-runner"]),
    ):
        main()
    captured = capsys.readouterr()
    assert "manage.py test accounts.tests.test_models" in captured.out
    assert "1 ran" in captured.out
    assert "1 passed" in captured.out
    assert "0 failed" in captured.out


def test_cli_dry_run_skips_subprocess(base_patches, capsys):
    with (
        patch("subprocess.run") as mock_run,
        patch("sys.argv", ["pr-test-runner", "--dry-run"]),
    ):
        main()
    mock_run.assert_not_called()
    assert "manage.py test accounts.tests.test_models" in capsys.readouterr().out


def test_cli_prints_error_and_exits_1_on_git_error(base_patches, capsys):
    with (
        patch("pr_test_runner.cli.get_repo_root", side_effect=GitError("Not a git repository.")),
        patch("sys.argv", ["pr-test-runner"]),
        pytest.raises(SystemExit) as exc_info,
    ):
        main()
    assert exc_info.value.code == 1
    assert "Not a git repository" in capsys.readouterr().err


def test_cli_prints_info_when_no_test_files_found(base_patches, capsys):
    with (
        patch("pr_test_runner.cli.get_pr_files", return_value=["accounts/models.py"]),
        patch("sys.argv", ["pr-test-runner"]),
    ):
        main()
    assert "No test files found" in capsys.readouterr().out


def test_cli_exits_1_when_any_test_fails(base_patches):
    with (
        patch("subprocess.run", return_value=make_proc(1)),
        patch("sys.argv", ["pr-test-runner"]),
        pytest.raises(SystemExit) as exc_info,
    ):
        main()
    assert exc_info.value.code == 1
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_cli.py -v
```

Expected: `ImportError: cannot import name 'main' from 'pr_test_runner.cli'`.

- [ ] **Step 3: Create pr_test_runner/cli.py**

```python
import argparse
import sys

from pr_test_runner.git import get_repo_root, get_current_branch, get_github_remote, GitError
from pr_test_runner.github import get_token, get_pr_files, GitHubError
from pr_test_runner.resolver import filter_test_files, path_to_module
from pr_test_runner.runner import load_config, run_tests, ConfigError


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run tests changed in the current branch's GitHub PR."
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Print commands without running them."
    )
    args = parser.parse_args()

    try:
        repo_root = get_repo_root()
        config = load_config(repo_root)
        branch = get_current_branch()
        owner, repo = get_github_remote()
        token = get_token()
        files = get_pr_files(owner, repo, branch, token)
    except (GitError, GitHubError, ConfigError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    test_files = filter_test_files(files)
    if not test_files:
        print("No test files found in PR. Nothing to run.")
        return

    modules = [path_to_module(f) for f in test_files]
    results = run_tests(modules, config["command"], dry_run=args.dry_run)

    passed = sum(1 for _, code in results if code == 0)
    failed = sum(1 for _, code in results if code != 0)
    total = len(results)
    print(f"\n--- Summary: {total} ran, {passed} passed, {failed} failed ---")

    if failed:
        sys.exit(1)
```

- [ ] **Step 4: Run all tests to verify everything passes**

```bash
pytest -v
```

Expected: All tests PASS (29 total across all test files).

- [ ] **Step 5: Smoke test the entry point**

```bash
pr-test-runner --help
```

Expected output:
```
usage: pr-test-runner [-h] [--dry-run]

Run tests changed in the current branch's GitHub PR.

options:
  -h, --help   show this help message and exit
  --dry-run    Print commands without running them.
```

- [ ] **Step 6: Commit**

```bash
git add pr_test_runner/cli.py tests/test_cli.py
git commit -m "feat: add CLI entry point and orchestration"
```
