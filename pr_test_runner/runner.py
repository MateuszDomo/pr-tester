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
