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
