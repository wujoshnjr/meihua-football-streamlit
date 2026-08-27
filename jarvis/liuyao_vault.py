from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "knowledge" / "liuyao_sources.json"


@lru_cache(maxsize=1)
def _catalog() -> dict[str, Any]:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def liuyao_catalog_stats() -> dict[str, Any]:
    payload = _catalog()
    return {
        "schema_version": payload["schema_version"],
        "status": payload["status"],
        "primary_classical_sources": len(payload.get("primary_classical", [])),
        "modern_teaching_sources": len(payload.get("modern_teaching", [])),
        "user_video_status": payload.get("user_provided_video", {}).get("retrieval_status"),
        "implemented_hexagrams": 64,
        "bagong_palaces": 8,
    }


def search_liuyao(query: str, *, limit: int = 12) -> list[dict[str, Any]]:
    needle = query.strip().lower()
    if not needle:
        return []

    payload = _catalog()
    rows: list[dict[str, Any]] = []
    for family, entries in (
        ("primary_classical", payload.get("primary_classical", [])),
        ("modern_teaching", payload.get("modern_teaching", [])),
    ):
        for entry in entries:
            haystack = json.dumps(entry, ensure_ascii=False).lower()
            if needle in haystack:
                rows.append(
                    {
                        "system": "LIUYAO",
                        "family": family,
                        **entry,
                    }
                )
    video = payload.get("user_provided_video") or {}
    if needle in json.dumps(video, ensure_ascii=False).lower():
        rows.append({"system": "LIUYAO", "family": "user_video", **video})
    return rows[:limit]
