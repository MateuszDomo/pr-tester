import argparse
import sys

from pr_test_runner.git import get_repo_root, get_current_branch, get_github_remote, GitError
from pr_test_runner.github import get_token, get_pr_files, GitHubError
from pr_test_runner.resolver import filter_test_files, path_to_module
from pr_test_runner.runner import load_config, run_tests, ConfigError


def main() -> None:
    parser = argparse.ArgumentParser(description="Run tests changed in the current branch's GitHub PR.")
    parser.add_argument("--dry-run", action="store_true", help="Print commands without running them.")
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
