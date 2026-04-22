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
