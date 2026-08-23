from __future__ import annotations

import argparse
import subprocess
import sys
import time


def run_with_retry(command: list[str], *, attempts: int, backoff_seconds: float) -> int:
    if attempts < 1:
        raise ValueError("attempts must be >= 1")
    if backoff_seconds < 0:
        raise ValueError("backoff_seconds must be >= 0")

    for attempt in range(1, attempts + 1):
        print(f"[retry] attempt {attempt}/{attempts}: {' '.join(command)}", flush=True)
        result = subprocess.run(command, check=False)
        if result.returncode == 0:
            return 0
        if attempt < attempts:
            delay = backoff_seconds * (2 ** (attempt - 1))
            print(
                f"[retry] command failed with exit={result.returncode}; retrying in {delay:.1f}s",
                file=sys.stderr,
                flush=True,
            )
            time.sleep(delay)

    return result.returncode


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run a command with bounded exponential-backoff retries."
    )
    parser.add_argument("--attempts", type=int, default=3)
    parser.add_argument("--backoff-seconds", type=float, default=2.0)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()

    command = list(args.command)
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        parser.error("a command is required after --")

    raise SystemExit(
        run_with_retry(
            command,
            attempts=args.attempts,
            backoff_seconds=args.backoff_seconds,
        )
    )


if __name__ == "__main__":
    main()
