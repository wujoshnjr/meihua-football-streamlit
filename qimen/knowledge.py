from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable


KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent / "knowledge"
KNOWLEDGE_FILES = (
    "entities.json",
    "calendar.json",
    "patterns.json",
    "methods.json",
    "sources.json",
)


@lru_cache(maxsize=1)
def load_knowledge() -> dict[str, Any]:
    """Load and merge all versioned knowledge files without mutating them."""

    merged: dict[str, Any] = {"files": {}, "records": []}
    for filename in KNOWLEDGE_FILES:
        path = KNOWLEDGE_DIR / filename
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        merged["files"][filename] = payload
        merged["records"].extend(_flatten_payload(filename, payload))
    return merged


def _flatten_payload(filename: str, payload: dict[str, Any]) -> Iterable[dict[str, Any]]:
    skip = {"schema_version", "scope_note", "source_policy", "interpretation_order"}
    for section, value in payload.items():
        if section in skip:
            continue
        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    yield _record(filename, section, item)
        elif isinstance(value, dict):
            if section == "active_method":
                yield _record(filename, section, value)
            elif section == "eighteen_ju":
                for dun, terms in value.items():
                    if not isinstance(terms, dict):
                        continue
                    for term, ju in terms.items():
                        yield _record(filename, section, {"name": f"{dun}・{term}", "ju": ju})


def _record(filename: str, section: str, item: dict[str, Any]) -> dict[str, Any]:
    record = dict(item)
    record["_file"] = filename
    record["_section"] = section
    record["_title"] = str(
        item.get("name")
        or item.get("key")
        or item.get("title")
        or item.get("family")
        or section
    )
    return record


def search_knowledge(query: str = "", section: str | None = None) -> list[dict[str, Any]]:
    records = load_knowledge()["records"]
    selected = records
    if section and section != "全部":
        selected = [row for row in selected if row["_section"] == section]
    normalized = query.strip().casefold()
    if normalized:
        selected = [
            row for row in selected
            if normalized in json.dumps(row, ensure_ascii=False).casefold()
        ]
    return selected


def knowledge_stats() -> dict[str, int]:
    records = load_knowledge()["records"]
    stats: dict[str, int] = {"total": len(records)}
    for row in records:
        section = row["_section"]
        stats[section] = stats.get(section, 0) + 1
    return stats
