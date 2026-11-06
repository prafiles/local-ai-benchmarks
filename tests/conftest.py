"""Shared fixtures. The harness scripts import each other by putting their own
directory on sys.path; tests do the same rather than packaging anything."""

import os
import subprocess
import sys

import pytest

HARNESS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "harness")
if HARNESS not in sys.path:
    sys.path.insert(0, HARNESS)


def _has_git():
    try:
        subprocess.run(["git", "--version"], capture_output=True, check=True)
        return True
    except Exception:
        return False


requires_git = pytest.mark.skipif(not _has_git(), reason="git binary not available")


@pytest.fixture
def git_repo(tmp_path):
    """An empty directory configured so git commands never read the user's
    global identity, gpg-sign, or template (mirrors the INIT fixture in
    b3_git.py, which does the same inside the sandbox)."""
    repo = tmp_path / "repo"
    repo.mkdir()
    env = {
        "GIT_AUTHOR_NAME": "tester",
        "GIT_AUTHOR_EMAIL": "a@b.c",
        "GIT_COMMITTER_NAME": "tester",
        "GIT_COMMITTER_EMAIL": "a@b.c",
        "GIT_CONFIG_GLOBAL": str(tmp_path / "empty.gitconfig"),
        "GIT_CONFIG_SYSTEM": str(tmp_path / "empty.gitconfig"),
        "HOME": str(tmp_path),
        "PATH": os.environ.get("PATH", ""),
    }
    return repo, env
