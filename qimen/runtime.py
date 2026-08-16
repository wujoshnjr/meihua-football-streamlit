from __future__ import annotations

import os


GIT_COMMIT_ENV_KEYS = (
    "GITHUB_SHA",
    "VERCEL_GIT_COMMIT_SHA",
    "RENDER_GIT_COMMIT",
    "SOURCE_VERSION",
)


def detect_git_commit() -> str:
    """Return a deployment-provided commit without invoking a shell command."""

    for key in GIT_COMMIT_ENV_KEYS:
        value = os.environ.get(key, "").strip().lower()
        if 7 <= len(value) <= 64 and all(character in "0123456789abcdef" for character in value):
            return value
    return "UNAVAILABLE_NOT_EXPORTED"


def is_formal_git_commit(value: str) -> bool:
    normalized = value.strip().lower()
    return 40 <= len(normalized) <= 64 and all(
        character in "0123456789abcdef" for character in normalized
    )
