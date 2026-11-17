"""
GitHub integration.

We keep this simple: we use the `git` command line tool to clone the
repository. For private repositories, a GitHub Personal Access Token (PAT) is
placed inside the clone URL, which is how GitHub expects tokens over HTTPS:

    https://<token>@github.com/owner/repo.git

The token is removed from every message before it is logged or shown.
"""

import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

# Matches https://github.com/owner/repo, with optional ".git" or trailing "/"
GITHUB_URL_PATTERN = re.compile(
    r"^https?://(www\.)?github\.com/(?P<owner>[A-Za-z0-9_.-]+)/(?P<repo>[A-Za-z0-9_.-]+?)(\.git)?/?$"
)

# Allowed characters in a branch name (blocks shell tricks like "; rm -rf")
BRANCH_PATTERN = re.compile(r"^[A-Za-z0-9._/-]{1,100}$")


class GitHubError(Exception):
    """Raised when a repository cannot be read or cloned."""


@dataclass
class RepoInfo:
    owner: str
    name: str
    clone_url: str  # https URL without token


@dataclass
class CloneResult:
    path: Path
    commit_id: str
    commit_message: str


def parse_github_url(url: str) -> RepoInfo:
    """Check the URL and split it into owner and repository name.

    A local folder path (starting with "/") is also accepted. This is used for
    the offline backup demo, where the sample app is a git repo on disk.
    """
    url = url.strip()
    if url.startswith("/"):
        name = Path(url).name or "local-repo"
        return RepoInfo(owner="local", name=name, clone_url=url)

    match = GITHUB_URL_PATTERN.match(url)
    if not match:
        raise GitHubError("Please enter a valid GitHub URL, for example https://github.com/user/my-app")
    owner, repo = match.group("owner"), match.group("repo")
    return RepoInfo(owner=owner, name=repo, clone_url=f"https://github.com/{owner}/{repo}.git")


def validate_branch(branch: str) -> str:
    branch = (branch or "").strip()
    if not BRANCH_PATTERN.match(branch) or branch.startswith("-") or ".." in branch:
        raise GitHubError(f"Invalid branch name: {branch!r}")
    return branch


def _url_with_token(clone_url: str, token: str) -> str:
    if token and clone_url.startswith("https://"):
        return clone_url.replace("https://", f"https://x-access-token:{token}@", 1)
    return clone_url


def _hide_token(text: str, token: str) -> str:
    return text.replace(token, "***") if token else text


def _run_git(args: list[str], token: str = "", cwd: Path | None = None, timeout: int = 120) -> str:
    """Run a git command and return its output. Raises GitHubError on failure."""
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            # Never wait for a username/password prompt in the terminal
            env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
        )
    except FileNotFoundError as exc:
        raise GitHubError("git is not installed on the server") from exc
    except subprocess.TimeoutExpired as exc:
        raise GitHubError("git took too long (check your internet connection)") from exc

    if result.returncode != 0:
        error = _hide_token(result.stderr.strip() or result.stdout.strip(), token)
        if "could not read Username" in error or "Authentication failed" in error or "not found" in error.lower():
            error += " -- If the repository is private, add a GitHub Personal Access Token."
        raise GitHubError(error)
    return result.stdout.strip()


def clone_repository(repo_url: str, branch: str, destination: Path, token: str = "") -> CloneResult:
    """Download the repository (only the latest commit of one branch)."""
    info = parse_github_url(repo_url)
    branch = validate_branch(branch)

    if destination.exists():
        shutil.rmtree(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)

    _run_git(
        ["clone", "--depth", "1", "--branch", branch, "--", _url_with_token(info.clone_url, token), str(destination)],
        token=token,
    )
    commit_id = _run_git(["rev-parse", "HEAD"], cwd=destination)
    commit_message = _run_git(["log", "-1", "--pretty=%s"], cwd=destination)

    # Remove the token from .git/config so it is not left on disk
    _run_git(["remote", "set-url", "origin", info.clone_url], cwd=destination)

    return CloneResult(path=destination, commit_id=commit_id, commit_message=commit_message[:300])


def list_remote_branches(repo_url: str, token: str = "") -> list[str]:
    """Return the branch names of a repository without cloning it."""
    info = parse_github_url(repo_url)
    output = _run_git(["ls-remote", "--heads", "--", _url_with_token(info.clone_url, token)], token=token, timeout=30)
    branches = []
    for line in output.splitlines():
        parts = line.split("refs/heads/")
        if len(parts) == 2:
            branches.append(parts[1])
    return sorted(branches)


def resolve_source_dir(repo_path: Path, root_directory: str) -> Path:
    """Return the folder that contains the app (supports monorepo sub-folders)."""
    root_directory = (root_directory or "").strip().strip("/")
    if not root_directory:
        return repo_path
    source = (repo_path / root_directory).resolve()
    # Stop paths like "../../etc" from escaping the cloned repository
    if repo_path.resolve() not in source.parents and source != repo_path.resolve():
        raise GitHubError("Root directory must be inside the repository")
    if not source.is_dir():
        raise GitHubError(f"Folder '{root_directory}' was not found in the repository")
    return source
