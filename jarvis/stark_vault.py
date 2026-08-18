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
    return list(_load_json("patterns.json").get("patterns", []))


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


def _qimen_protocol_context() -> list[dict[str, Any]]:
    payload = _load_json("interpretation.json")
    return [
        {
            "kind": "qimen_interpretation_policy",
            "schema_version": payload.get("schema_version"),
            "mapping_version": payload.get("mapping_version"),
            "scope_note": payload.get("scope_note"),
            "source_policy": payload.get("source_policy", []),
        }
    ]


def qimen_context(board: QimenBoard) -> list[dict[str, Any]]:
    """Retrieve source material relevant to one deterministic Qimen board.

    The vault never scores, ranks, or decides a match outcome. It supplies the
    objective chart facts and matching knowledge to the final AI interpreter.
    """

    base = _qimen_base_rows()
    context: list[dict[str, Any]] = _qimen_protocol_context()
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

        if state.is_void:
            relevant_keys.add("旬空")
        if state.is_horse:
            relevant_keys.add("驛馬")

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
    line_roles = _load_json("meihua_line_roles.json").get("line_roles", [])

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
    context: list[dict[str, Any]] = [
        {
            "kind": "meihua_method_policy",
            "method": rules.get("method"),
            "interpretation_order": rules.get("interpretation_order", []),
        }
    ]
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

    for row in line_roles:
        if row.get("line") == snapshot.moving_line:
            context.append({"kind": "meihua_moving_line_role", **row})
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
        "qimen_stems": len(qimen["stems"]),
        "qimen_patterns": len(_qimen_pattern_rows()),
        "meihua_trigrams": len(_load_json("meihua_trigrams.json").get("trigrams", [])),
        "meihua_hexagrams": len(_load_json("meihua_hexagrams.json").get("hexagrams", [])),
        "meihua_body_use_relations": len(_load_json("meihua_rules.json").get("body_use_relations", [])),
        "meihua_line_roles": len(_load_json("meihua_line_roles.json").get("line_roles", [])),
    }


def _search_rows(results: list[dict[str, Any]], system: str, family: str, rows: Iterable[dict[str, Any]], term: str) -> None:
    for row in rows:
        if term in json.dumps(row, ensure_ascii=False).lower():
            results.append({"system": system, "family": family, **row})


def search_vault(query: str) -> list[dict[str, Any]]:
    term = query.strip().lower()
    if not term:
        return []
    results: list[dict[str, Any]] = []

    qimen = _qimen_base_rows()
    for family, rows in qimen.items():
        _search_rows(results, "QIMEN_DUNJIA", family, rows, term)
    _search_rows(results, "QIMEN_DUNJIA", "patterns", _qimen_pattern_rows(), term)

    ontology = _load_json("football_ontology.json").get("mappings", {})
    if isinstance(ontology, dict):
        for family, rows in ontology.items():
            if isinstance(rows, list):
                _search_rows(results, "QIMEN_DUNJIA", f"football:{family}", rows, term)

    interpretation = _load_json("interpretation.json")
    if term in json.dumps(interpretation, ensure_ascii=False).lower():
        results.append(
            {
                "system": "QIMEN_DUNJIA",
                "family": "interpretation_protocol",
                "schema_version": interpretation.get("schema_version"),
                "scope_note": interpretation.get("scope_note"),
                "source_policy": interpretation.get("source_policy", []),
            }
        )

    _search_rows(
        results,
        "MEIHUA_YISHU",
        "trigrams",
        _load_json("meihua_trigrams.json").get("trigrams", []),
        term,
    )
    _search_rows(
        results,
        "MEIHUA_YISHU",
        "hexagrams",
        _load_json("meihua_hexagrams.json").get("hexagrams", []),
        term,
    )
    _search_rows(
        results,
        "MEIHUA_YISHU",
        "body_use",
        _load_json("meihua_rules.json").get("body_use_relations", []),
        term,
    )
    _search_rows(
        results,
        "MEIHUA_YISHU",
        "line_roles",
        _load_json("meihua_line_roles.json").get("line_roles", []),
        term,
    )
    return results[:100]
