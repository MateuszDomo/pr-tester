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
