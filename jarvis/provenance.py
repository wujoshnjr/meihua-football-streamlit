from __future__ import annotations

import hashlib
import json
import os
from typing import Any


GIT_COMMIT_ENV_KEYS = (
    "GITHUB_SHA",
    "VERCEL_GIT_COMMIT_SHA",
    "RENDER_GIT_COMMIT",
    "SOURCE_VERSION",
)


def canonical_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_payload(payload: Any) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def detect_git_commit() -> str:
    """Return a deployment-provided commit without invoking a shell command."""

    for key in GIT_COMMIT_ENV_KEYS:
        value = os.environ.get(key, "").strip().lower()
        if 7 <= len(value) <= 64 and all(character in "0123456789abcdef" for character in value):
            return value
    return "UNAVAILABLE_NOT_EXPORTED"
