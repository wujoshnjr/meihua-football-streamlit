from __future__ import annotations

import ast
import subprocess
import sys
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _imported_roots(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".", 1)[0])
    return roots


def test_app_startup_does_not_directly_import_native_data_stack() -> None:
    forbidden = {"pandas", "numpy", "pyarrow", "openpyxl"}
    assert _imported_roots(ROOT / "app.py").isdisjoint(forbidden)
    assert _imported_roots(ROOT / "storage.py").isdisjoint(forbidden)


def test_casting_runtime_cannot_import_the_post_match_evaluator() -> None:
    casting_runtime = (
        "app.py",
        "casting_structure.py",
        "conditional_meanings.py",
        "export_builder.py",
        "html_report_builder.py",
        "knowledge_loader.py",
        "meihua_engine.py",
        "najia_structure.py",
        "report_builder.py",
        "storage.py",
    )
    for filename in casting_runtime:
        assert "forecast_evaluation" not in _imported_roots(ROOT / filename)


def test_bare_app_startup_does_not_load_native_data_modules() -> None:
    probe = (
        "import sys; import app; "
        "forbidden={'pandas','numpy','pyarrow','openpyxl'}; "
        "loaded=forbidden.intersection(sys.modules); "
        "assert not loaded, loaded"
    )
    completed = subprocess.run(
        [sys.executable, "-c", probe],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_streamlit_cloud_file_watcher_is_disabled() -> None:
    with (ROOT / ".streamlit" / "config.toml").open("rb") as handle:
        config = tomllib.load(handle)
    assert config["server"]["headless"] is True
    assert config["server"]["fileWatcherType"] == "none"
    assert config["server"]["runOnSave"] is False
