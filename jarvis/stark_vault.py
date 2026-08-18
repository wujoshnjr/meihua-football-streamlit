from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from meihua.engine import MeihuaSnapshot
from qimen.models import QimenBoard


ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE_ROOT = ROOT / "knowledge"


def _load_json(name: str) -> dict[str, Any]:
    return json.loads((KNOWLEDGE_ROOT / name).read_text(encoding="utf-8"))


def _by_key(rows: Iterable[dict[str, Any]], key: str) -> dict[str, Any] | None:
    for row in rows:
        if row.get("key") == key or row.get("name") == key:
            return row
    return None


def _qimen_base_rows() -> dict[str, list[dict[str, Any]]]:
    payload = _load_json("entities.json")
    return {
        "palaces": list(payload.get("palaces", [])),
        "doors": list(payload.get("doors", [])),
        "stars": list(payload.get("stars", [])),
        "deities": list(payload.get("deities", [])),
        "stems": list(payload.get("stems", [])),
    }


def _qimen_pattern_rows() -> list[dict[str, Any]]:
    payload = _load_json("patterns.json")
    for key in ("patterns", "items", "entries"):
        if isinstance(payload.get(key), list):
            return list(payload[key])
    return []


def _football_mapping_rows(keys: set[str]) -> list[dict[str, Any]]:
    payload = _load_json("football_ontology.json")
    found: list[dict[str, Any]] = []
    mappings = payload.get("mappings", {})
    if isinstance(mappings, dict):
        for family, rows in mappings.items():
            if not isinstance(rows, list):
                continue
            for row in rows:
                if str(row.get("key", "")) in keys:
                    found.append({"kind": f"football_mapping:{family}", **row})
    return found


def qimen_context(board: QimenBoard) -> list[dict[str, Any]]:
    """Return knowledge entries relevant to the deterministic Qimen board.

    This function retrieves source material only. It does not score, rank, or decide
    a match outcome; final synthesis belongs to the AI interpreter.
    """

    base = _qimen_base_rows()
    context: list[dict[str, Any]] = []
    relevant_keys: set[str] = set()

    for number in sorted(board.palaces):
        state = board.palaces[number]
        relevant_keys.add(state.name)
        palace = _by_key(base["palaces"], state.name)
        if palace:
            context.append({"kind": "qimen_palace", "palace": number, **palace})

        if state.door:
            relevant_keys.add(state.door)
            door = _by_key(base["doors"], state.door)
            if door:
                context.append({"kind": "qimen_door", "palace": number, **door})

        for star_name in state.stars:
            relevant_keys.add(star_name)
            star = _by_key(base["stars"], star_name)
            if star:
                context.append({"kind": "qimen_star", "palace": number, **star})

        if state.deity:
            relevant_keys.add(state.deity)
            deity = _by_key(base["deities"], state.deity)
            if deity:
                context.append({"kind": "qimen_deity", "palace": number, **deity})

        for stem_name in [state.earth_stem, *state.earth_hidden_stems, *state.heaven_stems]:
            relevant_keys.add(stem_name)
            stem = _by_key(base["stems"], stem_name)
            if stem:
                context.append({"kind": "qimen_stem", "palace": number, **stem})

    patterns = _qimen_pattern_rows()
    for hit in board.patterns:
        row = _by_key(patterns, hit.name)
        context.append(
            {
                "kind": "qimen_pattern",
                "name": hit.name,
                "category": hit.category,
                "palace": hit.palace,
                "condition": hit.condition,
                "reading": hit.reading,
                "caution": hit.caution,
                "source_id": hit.source_id,
                "catalog_entry": row,
            }
        )
        relevant_keys.add(hit.name)

    context.extend(_football_mapping_rows(relevant_keys))
    return context


def meihua_hexagram(upper: str, lower: str) -> dict[str, Any]:
    payload = _load_json("meihua_hexagrams.json")
    for row in payload.get("hexagrams", []):
        if row.get("upper") == upper and row.get("lower") == lower:
            return row
    raise KeyError(f"找不到梅花卦象：{upper}上 {lower}下")


def meihua_context(snapshot: MeihuaSnapshot) -> list[dict[str, Any]]:
    trigrams = _load_json("meihua_trigrams.json").get("trigrams", [])
    rules = _load_json("meihua_rules.json")

    names = {
        snapshot.upper_trigram,
        snapshot.lower_trigram,
        snapshot.body_trigram,
        snapshot.use_trigram,
        snapshot.mutual_upper_trigram,
        snapshot.mutual_lower_trigram,
        snapshot.changed_upper_trigram,
        snapshot.changed_lower_trigram,
        snapshot.changed_use_trigram,
    }
    context: list[dict[str, Any]] = []
    for name in sorted(names):
        row = _by_key(trigrams, name)
        if row:
            context.append({"kind": "meihua_trigram", **row})

    original = meihua_hexagram(snapshot.upper_trigram, snapshot.lower_trigram)
    mutual = meihua_hexagram(snapshot.mutual_upper_trigram, snapshot.mutual_lower_trigram)
    changed = meihua_hexagram(snapshot.changed_upper_trigram, snapshot.changed_lower_trigram)
    context.extend(
        [
            {"kind": "meihua_original_hexagram", **original},
            {"kind": "meihua_mutual_hexagram", **mutual},
            {"kind": "meihua_changed_hexagram", **changed},
        ]
    )

    for row in rules.get("body_use_relations", []):
        if row.get("relation") == snapshot.body_use_relation:
            context.append({"kind": "meihua_body_use", **row})
            break
    context.append(
        {
            "kind": "meihua_seasonal_state",
            "body_trigram": snapshot.body_trigram,
            "state": snapshot.body_season_state,
            "note": "旺衰必須與體用生克、互卦、變卦、動爻合參，不可單項定吉凶。",
        }
    )
    return context


def vault_stats() -> dict[str, int]:
    qimen = _qimen_base_rows()
    return {
        "qimen_palaces": len(qimen["palaces"]),
        "qimen_doors": len(qimen["doors"]),
        "qimen_stars": len(qimen["stars"]),
        "qimen_deities": len(qimen["deities"]),
        "qimen_patterns": len(_qimen_pattern_rows()),
        "meihua_trigrams": len(_load_json("meihua_trigrams.json").get("trigrams", [])),
        "meihua_hexagrams": len(_load_json("meihua_hexagrams.json").get("hexagrams", [])),
        "meihua_body_use_relations": len(_load_json("meihua_rules.json").get("body_use_relations", [])),
    }


def search_vault(query: str) -> list[dict[str, Any]]:
    term = query.strip().lower()
    if not term:
        return []
    results: list[dict[str, Any]] = []

    qimen = _qimen_base_rows()
    for family, rows in qimen.items():
        for row in rows:
            if term in json.dumps(row, ensure_ascii=False).lower():
                results.append({"system": "QIMEN_DUNJIA", "family": family, **row})

    for row in _qimen_pattern_rows():
        if term in json.dumps(row, ensure_ascii=False).lower():
            results.append({"system": "QIMEN_DUNJIA", "family": "patterns", **row})

    for row in _load_json("meihua_trigrams.json").get("trigrams", []):
        if term in json.dumps(row, ensure_ascii=False).lower():
            results.append({"system": "MEIHUA_YISHU", "family": "trigrams", **row})

    for row in _load_json("meihua_hexagrams.json").get("hexagrams", []):
        if term in json.dumps(row, ensure_ascii=False).lower():
            results.append({"system": "MEIHUA_YISHU", "family": "hexagrams", **row})

    for row in _load_json("meihua_rules.json").get("body_use_relations", []):
        if term in json.dumps(row, ensure_ascii=False).lower():
            results.append({"system": "MEIHUA_YISHU", "family": "body_use", **row})

    return results[:100]
