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
