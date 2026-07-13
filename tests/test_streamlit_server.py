from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app.py"


def _unused_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def test_streamlit_server_reaches_health_endpoint() -> None:
    """Start the real CLI so a server-level crash cannot hide behind AppTest."""

    port = _unused_port()
    command = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(APP),
        "--server.headless=true",
        "--server.address=127.0.0.1",
        f"--server.port={port}",
        "--browser.gatherUsageStats=false",
    ]
    environment = {**os.environ, "STREAMLIT_BROWSER_GATHER_USAGE_STATS": "false"}
    process = subprocess.Popen(
        command,
        cwd=ROOT,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    try:
        deadline = time.monotonic() + 20
        last_error = "health endpoint not ready"
        while time.monotonic() < deadline:
            if process.poll() is not None:
                output = process.stdout.read() if process.stdout else ""
                raise AssertionError(
                    f"Streamlit exited with code {process.returncode}.\n{output}"
                )
            try:
                with urlopen(
                    f"http://127.0.0.1:{port}/_stcore/health", timeout=1
                ) as response:
                    body = response.read().decode("utf-8").strip().lower()
                    assert response.status == 200
                    assert body == "ok"
                    return
            except (OSError, URLError) as exc:
                last_error = str(exc)
                time.sleep(0.2)

        output = process.stdout.read() if process.poll() is not None and process.stdout else ""
        raise AssertionError(f"Streamlit health check timed out: {last_error}\n{output}")
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
