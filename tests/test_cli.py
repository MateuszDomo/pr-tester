import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from pr_test_runner.cli import main

def test_main_no_test_files(capsys):
    with patch("pr_test_runner.cli.get_repo_root", return_value=Path("/repo")), \
         patch("pr_test_runner.cli.load_config", return_value={"command": "python -m pytest {module}"}), \
         patch("pr_test_runner.cli.get_current_branch", return_value="feature-branch"), \
         patch("pr_test_runner.cli.get_github_remote", return_value=("owner", "repo")), \
         patch("pr_test_runner.cli.get_token", return_value="token"), \
         patch("pr_test_runner.cli.get_pr_files", return_value=["README.md", "setup.py"]), \
         patch("sys.argv", ["pr-test-runner"]):
        main()
    out = capsys.readouterr().out
    assert "No test files found" in out

def test_main_exits_1_on_failure(capsys):
    with patch("pr_test_runner.cli.get_repo_root", return_value=Path("/repo")), \
         patch("pr_test_runner.cli.load_config", return_value={"command": "python -m pytest {module}"}), \
         patch("pr_test_runner.cli.get_current_branch", return_value="feature-branch"), \
         patch("pr_test_runner.cli.get_github_remote", return_value=("owner", "repo")), \
         patch("pr_test_runner.cli.get_token", return_value="token"), \
         patch("pr_test_runner.cli.get_pr_files", return_value=["app/tests/test_views.py"]), \
         patch("pr_test_runner.cli.run_tests", return_value=[("app.tests.test_views", 1)]), \
         patch("sys.argv", ["pr-test-runner"]):
        with pytest.raises(SystemExit) as exc_info:
            main()
    assert exc_info.value.code == 1

def test_main_exits_0_on_success(capsys):
    with patch("pr_test_runner.cli.get_repo_root", return_value=Path("/repo")), \
         patch("pr_test_runner.cli.load_config", return_value={"command": "python -m pytest {module}"}), \
         patch("pr_test_runner.cli.get_current_branch", return_value="feature-branch"), \
         patch("pr_test_runner.cli.get_github_remote", return_value=("owner", "repo")), \
         patch("pr_test_runner.cli.get_token", return_value="token"), \
         patch("pr_test_runner.cli.get_pr_files", return_value=["app/tests/test_views.py"]), \
         patch("pr_test_runner.cli.run_tests", return_value=[("app.tests.test_views", 0)]), \
         patch("sys.argv", ["pr-test-runner"]):
        main()  # should not raise
    out = capsys.readouterr().out
    assert "1 ran" in out
    assert "1 passed" in out
    assert "0 failed" in out

def test_main_git_error_exits_1(capsys):
    from pr_test_runner.git import GitError
    with patch("pr_test_runner.cli.get_repo_root", side_effect=GitError("Not a git repo")), \
         patch("sys.argv", ["pr-test-runner"]):
        with pytest.raises(SystemExit) as exc_info:
            main()
    assert exc_info.value.code == 1
    err = capsys.readouterr().err
    assert "Error:" in err

def test_main_dry_run_passes_flag():
    with patch("pr_test_runner.cli.get_repo_root", return_value=Path("/repo")), \
         patch("pr_test_runner.cli.load_config", return_value={"command": "python -m pytest {module}"}), \
         patch("pr_test_runner.cli.get_current_branch", return_value="feature-branch"), \
         patch("pr_test_runner.cli.get_github_remote", return_value=("owner", "repo")), \
         patch("pr_test_runner.cli.get_token", return_value="token"), \
         patch("pr_test_runner.cli.get_pr_files", return_value=["app/tests/test_views.py"]), \
         patch("pr_test_runner.cli.run_tests", return_value=[("app.tests.test_views", 0)]) as mock_run, \
         patch("sys.argv", ["pr-test-runner", "--dry-run"]):
        main()
    mock_run.assert_called_once_with(["app.tests.test_views"], "python -m pytest {module}", dry_run=True)
