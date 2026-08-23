from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import sys

from streamlit.testing.v1 import AppTest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import run_with_retry as retry_module  # noqa: E402


def test_run_with_retry_recovers_after_transient_failures(monkeypatch) -> None:
    return_codes = iter([1, 1, 0])
    calls: list[list[str]] = []
    sleeps: list[float] = []

    def fake_run(command, check=False):
        assert check is False
        calls.append(list(command))
        return SimpleNamespace(returncode=next(return_codes))

    monkeypatch.setattr(retry_module.subprocess, "run", fake_run)
    monkeypatch.setattr(retry_module.time, "sleep", sleeps.append)

    result = retry_module.run_with_retry(
        ["python", "tools/import_zhouyi_kanripo.py"],
        attempts=3,
        backoff_seconds=0.5,
    )

    assert result == 0
    assert len(calls) == 3
    assert sleeps == [0.5, 1.0]


def test_run_with_retry_returns_final_failure(monkeypatch) -> None:
    monkeypatch.setattr(
        retry_module.subprocess,
        "run",
        lambda command, check=False: SimpleNamespace(returncode=7),
    )
    monkeypatch.setattr(retry_module.time, "sleep", lambda seconds: None)

    assert retry_module.run_with_retry(["false"], attempts=2, backoff_seconds=0) == 7


def test_yuanling_streamlit_page_smoke_loads_without_exception() -> None:
    app = AppTest.from_file(str(ROOT / "pages" / "6_Yuanling_Yanshu.py"))
    app.run(timeout=15)

    assert not app.exception
    assert app.title[0].value == "🔢 《元靈經》演數七要 / 日奇門"
