from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .integrity import canonical_json


def append_jsonl(path: str | Path, bundle: dict[str, Any]) -> Path:
    """Append an immutable research bundle to a local JSONL archive."""

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("a", encoding="utf-8") as handle:
        handle.write(canonical_json(bundle) + "\n")
    return destination


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    source = Path(path)
    if not source.exists():
        return []
    rows: list[dict[str, Any]] = []
    with source.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{source} 第 {line_number} 行不是合法 JSON") from exc
    return rows
