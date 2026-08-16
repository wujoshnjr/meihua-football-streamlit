from __future__ import annotations

import os

from qimen.runtime import detect_git_commit, is_formal_git_commit


def test_git_commit_is_read_only_from_known_deployment_environment():
    original = os.environ.get("GITHUB_SHA")
    try:
        os.environ["GITHUB_SHA"] = "A" * 40
        assert detect_git_commit() == "a" * 40
        assert is_formal_git_commit(detect_git_commit())
    finally:
        if original is None:
            os.environ.pop("GITHUB_SHA", None)
        else:
            os.environ["GITHUB_SHA"] = original


def test_short_commit_is_traceable_but_not_formal_for_activation_gate():
    assert not is_formal_git_commit("abcdef0")
    assert not is_formal_git_commit("UNAVAILABLE_NOT_EXPORTED")
