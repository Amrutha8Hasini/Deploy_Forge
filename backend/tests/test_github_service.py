"""Tests for GitHub integration (Module 2).

The clone test uses a git repository created on disk, so it needs `git` but
no internet connection.
"""

import subprocess

import pytest

from app.services.github_service import (
    GitHubError,
    _hide_token,
    _url_with_token,
    clone_repository,
    parse_github_url,
    resolve_source_dir,
    validate_branch,
)


@pytest.mark.parametrize(
    "url",
    [
        "https://github.com/octocat/Hello-World",
        "https://github.com/octocat/Hello-World.git",
        "https://github.com/octocat/Hello-World/",
        "http://www.github.com/octocat/Hello-World",
    ],
)
def test_parse_valid_urls(url):
    info = parse_github_url(url)
    assert info.owner == "octocat"
    assert info.name == "Hello-World"
    assert info.clone_url == "https://github.com/octocat/Hello-World.git"


@pytest.mark.parametrize(
    "url", ["", "github.com/a/b", "https://gitlab.com/a/b", "https://github.com/onlyowner", "https://github.com/a/b/c"]
)
def test_parse_invalid_urls(url):
    with pytest.raises(GitHubError):
        parse_github_url(url)


def test_local_path_is_accepted_for_offline_demo():
    info = parse_github_url("/demo-repos/deployforge-sample")
    assert info.owner == "local"
    assert info.name == "deployforge-sample"


@pytest.mark.parametrize("branch", ["main", "develop", "feature/login", "release-1.0"])
def test_valid_branches(branch):
    assert validate_branch(branch) == branch


@pytest.mark.parametrize("branch", ["", "-delete", "a;rm -rf /", "a..b", "has space"])
def test_invalid_branches(branch):
    with pytest.raises(GitHubError):
        validate_branch(branch)


def test_token_is_added_and_hidden():
    url = _url_with_token("https://github.com/a/b.git", "ghp_secret")
    assert url == "https://x-access-token:ghp_secret@github.com/a/b.git"
    assert _hide_token("fatal: https://ghp_secret@github.com", "ghp_secret") == "fatal: https://***@github.com"


def test_resolve_source_dir(tmp_path):
    (tmp_path / "sample-app").mkdir()
    assert resolve_source_dir(tmp_path, "") == tmp_path
    assert resolve_source_dir(tmp_path, "sample-app/") == (tmp_path / "sample-app").resolve()
    with pytest.raises(GitHubError):
        resolve_source_dir(tmp_path, "missing")
    with pytest.raises(GitHubError):
        resolve_source_dir(tmp_path, "../..")


def test_clone_local_repository(tmp_path):
    source = tmp_path / "source-repo"
    source.mkdir()
    (source / "app.py").write_text("print('hello')\n")

    def git(*args):
        subprocess.run(["git", *args], cwd=source, check=True, capture_output=True)

    git("init", "-b", "main")
    git("add", ".")
    git("-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-m", "First commit")

    result = clone_repository(str(source), "main", tmp_path / "clone")
    assert (result.path / "app.py").is_file()
    assert len(result.commit_id) == 40
    assert result.commit_message == "First commit"


def test_clone_missing_branch_fails(tmp_path):
    source = tmp_path / "repo"
    source.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=source, check=True, capture_output=True)
    with pytest.raises(GitHubError):
        clone_repository(str(source), "does-not-exist", tmp_path / "clone")
