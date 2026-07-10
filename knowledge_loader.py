from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent
KNOWLEDGE_DIR = BASE_DIR / "knowledge"


@lru_cache(maxsize=1)
def load_trigrams() -> dict[str, dict[str, Any]]:
    return _load_json(KNOWLEDGE_DIR / "trigrams.json")


@lru_cache(maxsize=1)
def load_hexagrams() -> dict[str, dict[str, Any]]:
    return _load_json(KNOWLEDGE_DIR / "hexagrams.json")


@lru_cache(maxsize=1)
def load_calibration_rules() -> list[dict[str, Any]]:
    payload = _load_json(KNOWLEDGE_DIR / "calibration_rules.json")
    if not isinstance(payload, list):
        raise ValueError("calibration_rules.json 必須是 JSON 陣列")
    return payload


def _load_json(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(f"找不到知識庫檔案：{path}")
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def clear_knowledge_cache() -> None:
    load_trigrams.cache_clear()
    load_hexagrams.cache_clear()
    load_calibration_rules.cache_clear()
