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
