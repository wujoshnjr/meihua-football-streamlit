from __future__ import annotations

import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from urllib.parse import urlparse


DEFAULT_ATTEMPTS = 5
DEFAULT_TIMEOUT_SECONDS = 60
DEFAULT_BACKOFF_SECONDS = (1.0, 2.0, 4.0, 8.0)


@dataclass(frozen=True)
class FetchFailure:
    url: str
    error_type: str
    message: str


class SourceFetchError(RuntimeError):
    pass


def _official_github_candidates(url: str) -> tuple[str, ...]:
    """Return equivalent official GitHub URLs without changing the pinned ref.

    The corpus importers pin immutable commit SHAs.  A fallback may change only
    the GitHub delivery endpoint, never owner/repo/ref/path.
    """

    parsed = urlparse(url)
    if parsed.netloc != "raw.githubusercontent.com":
        return (url,)

    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 4:
        return (url,)
    owner, repo, ref, *path_parts = parts
    path = "/".join(path_parts)
    alternate = f"https://github.com/{owner}/{repo}/raw/{ref}/{path}"
    return (url, alternate)


def _configured_attempts() -> int:
    raw = os.getenv("JARVIS_SOURCE_FETCH_ATTEMPTS", str(DEFAULT_ATTEMPTS))
    try:
        attempts = int(raw)
    except ValueError as exc:
        raise ValueError("JARVIS_SOURCE_FETCH_ATTEMPTS must be an integer") from exc
    if attempts < 1 or attempts > 10:
        raise ValueError("JARVIS_SOURCE_FETCH_ATTEMPTS must be between 1 and 10")
    return attempts


def fetch_pinned_bytes(
    url: str,
    *,
    user_agent: str,
    attempts: int | None = None,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> bytes:
    """Fetch immutable source bytes with bounded retry and endpoint fallback.

    This is resilience only.  It never falls forward to a branch name, latest
    revision, mirror with different content, or local generated corpus.
    """

    max_attempts = attempts if attempts is not None else _configured_attempts()
    if max_attempts < 1:
        raise ValueError("attempts must be >= 1")

    candidates = _official_github_candidates(url)
    failures: list[FetchFailure] = []
    retryable = (
        urllib.error.URLError,
        ConnectionError,
        TimeoutError,
        OSError,
    )

    for round_index in range(max_attempts):
        for candidate in candidates:
            request = urllib.request.Request(candidate, headers={"User-Agent": user_agent})
            try:
                with urllib.request.urlopen(request, timeout=timeout) as response:
                    payload = response.read()
                if not payload:
                    raise SourceFetchError(f"empty response from {candidate}")
                return payload
            except retryable as exc:
                failures.append(
                    FetchFailure(
                        url=candidate,
                        error_type=type(exc).__name__,
                        message=str(exc),
                    )
                )
            except SourceFetchError as exc:
                failures.append(
                    FetchFailure(
                        url=candidate,
                        error_type=type(exc).__name__,
                        message=str(exc),
                    )
                )

        if round_index + 1 < max_attempts:
            delay = DEFAULT_BACKOFF_SECONDS[min(round_index, len(DEFAULT_BACKOFF_SECONDS) - 1)]
            time.sleep(delay)

    tail = failures[-min(4, len(failures)) :]
    detail = "; ".join(f"{row.error_type} @ {row.url}: {row.message}" for row in tail)
    raise SourceFetchError(
        f"failed to fetch pinned source after {max_attempts} rounds; "
        f"ref was never changed. Recent failures: {detail}"
    )
