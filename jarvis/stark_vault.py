from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from meihua.engine import CONTROLS, GENERATES, TRIGRAM_ELEMENT, MeihuaSnapshot
from qimen.models import QimenBoard

from .qimen_relations import all_relations, relations_for_palace


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
    deep = _load_json("qimen_deep_layers.json")
    return [
        {
            "kind": "qimen_interpretation_policy",
            "schema_version": payload.get("schema_version"),
            "mapping_version": payload.get("mapping_version"),
            "scope_note": payload.get("scope_note"),
            "source_policy": payload.get("source_policy", []),
            "relation_contract": payload.get("relation_contract", {}),
        },
        {
            "kind": "qimen_deep_reading_policy",
            "schema_version": deep.get("schema_version"),
            "reading_hierarchy": deep.get("reading_hierarchy", []),
            "football_dimensions": deep.get("football_dimensions", []),
            "ai_rule": deep.get("ai_rule"),
            "scope_note": deep.get("scope_note"),
        },
    ]


def _qimen_palace_deep_profile(board: QimenBoard, number: int) -> dict[str, Any]:
    state = board.palaces[number]
    deep = _load_json("qimen_deep_layers.json")
    deity = deep.get("deity_modulation", {}).get(state.deity or "")
    modifiers: list[dict[str, Any]] = []
    if state.is_void:
        modifiers.append({"name": "旬空", **deep["state_modifiers"]["旬空"]})
    if state.is_horse:
        modifiers.append({"name": "驛馬", **deep["state_modifiers"]["驛馬"]})
    for hit in board.patterns:
        if hit.palace not in {None, number}:
            continue
        detail = deep.get("state_modifiers", {}).get(hit.name)
        if detail:
            modifiers.append({"name": hit.name, **detail})

    relation_rows = [row.to_dict() for row in relations_for_palace(state)]
    star_text = "、".join(state.stars) or "—"
    heaven_text = "、".join(state.heaven_stems) or "—"
    return {
        "kind": "qimen_palace_deep_profile",
        "palace": number,
        "palace_name": state.name,
        "stack": {
            "environment": state.name,
            "door_action": state.door,
            "star_capability": list(state.stars),
            "deity_modulation": state.deity,
            "heaven_trigger": list(state.heaven_stems),
            "earth_foundation": [state.earth_stem, *state.earth_hidden_stems],
        },
        "reading_prompt": (
            f"依宮→門→星→神→天地盤干→格局／空馬讀 {state.name}："
            f"門={state.door or '—'}；星={star_text}；神={state.deity or '—'}；"
            f"天盤={heaven_text}；地盤={state.earth_stem}。"
        ),
        "deity_detail": deity,
        "active_modifiers": modifiers,
        "active_relations": relation_rows,
        "football_questions": [
            "此宮的環境是否支持門的行動方式？",
            "星的能力是否被宮、門或空墓迫制削弱？",
            "八神是在放大、隱藏、連結、激化還是拖慢此宮作用？",
            "天地盤干呈現的外顯觸發與底層條件是否一致？",
            "足球場上有哪些可觀察證據支持？有哪些反證？",
        ],
    }


def qimen_context(board: QimenBoard) -> list[dict[str, Any]]:
    """Retrieve all knowledge layers that are active in one deterministic Qimen board.

    Base symbols, actual palace relationships, structural patterns, deep palace
    synthesis and matching football semantics are supplied to the AI. The vault
    never turns them into a final result, probability, or fixed score.
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

        for relation in relations_for_palace(state):
            context.append({"kind": "qimen_relation", "palace": number, **relation.to_dict()})

        if state.is_void:
            relevant_keys.add("旬空")
            context.append(
                {
                    "kind": "qimen_modifier",
                    "palace": number,
                    "name": "旬空",
                    "general_interpretation": "此宮處在旬空狀態，象意宜看暫不受力、落空、延後或需要外部填實；不可單憑空亡判吉凶。",
                    "football_meaning": "可能對應名單未落實、戰術訊號未兌現、機會有形無實或某條進攻／防守通道暫時失效。",
                    "observable_signals": ["預期主力／戰術沒有實際發揮", "場面優勢未轉成有效機會"],
                    "counter_signals": ["相關宮位代表的功能持續穩定兌現", "盤前不確定事項已正式落實且場上有效"],
                }
            )
        if state.is_horse:
            relevant_keys.add("驛馬")
            context.append(
                {
                    "kind": "qimen_modifier",
                    "palace": number,
                    "name": "驛馬",
                    "general_interpretation": "驛馬主動、移、奔走與位置變化；須合看所在宮與其他層，不自動等於吉或凶。",
                    "football_meaning": "可能對應快速轉換、頻繁換位、邊路縱深、遠征／旅途或比賽節奏突然加速。",
                    "observable_signals": ["快速攻守轉換", "球員頻繁換位或大範圍移動"],
                    "counter_signals": ["比賽長時間低速靜態", "相關球員／區域幾乎沒有位移與轉換"],
                }
            )

        context.append(_qimen_palace_deep_profile(board, number))

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


def _meihua_element_relation(lower: str, upper: str, deep: dict[str, Any]) -> dict[str, Any]:
    lower_element = TRIGRAM_ELEMENT[lower]
    upper_element = TRIGRAM_ELEMENT[upper]
    logic = deep["trigram_pair_logic"]
    if lower_element == upper_element:
        code = "same_element"
    elif GENERATES[lower_element] == upper_element:
        code = "lower_generates_upper"
    elif GENERATES[upper_element] == lower_element:
        code = "upper_generates_lower"
    elif CONTROLS[lower_element] == upper_element:
        code = "lower_controls_upper"
    else:
        code = "upper_controls_lower"
    return {
        "code": code,
        "lower": lower,
        "lower_element": lower_element,
        "upper": upper,
        "upper_element": upper_element,
        "interpretation": logic[code],
    }


def _meihua_stage_profile(
    kind: str,
    upper: str,
    lower: str,
    hexagram: dict[str, Any],
    deep: dict[str, Any],
    trigrams: list[dict[str, Any]],
) -> dict[str, Any]:
    upper_row = _by_key(trigrams, upper) or {"name": upper}
    lower_row = _by_key(trigrams, lower) or {"name": lower}
    return {
        "stage": kind,
        "stage_role": deep["hexagram_roles"][kind],
        "hexagram": hexagram,
        "upper_role": {**deep["upper_lower_roles"]["upper"], "trigram": upper_row},
        "lower_role": {**deep["upper_lower_roles"]["lower"], "trigram": lower_row},
        "upper_lower_element_relation": _meihua_element_relation(lower, upper, deep),
    }


def _meihua_deep_profile(
    snapshot: MeihuaSnapshot,
    original: dict[str, Any],
    mutual: dict[str, Any],
    changed: dict[str, Any],
    trigrams: list[dict[str, Any]],
) -> dict[str, Any]:
    deep = _load_json("meihua_deep_layers.json")
    body_use = deep["body_use_principles"][snapshot.body_use_relation]
    strength = deep["strength_rules"][snapshot.body_season_state]
    line = deep["moving_line_depth"][str(snapshot.moving_line)]
    return {
        "kind": "meihua_deep_profile",
        "schema_version": deep["schema_version"],
        "scope_note": deep["scope_note"],
        "original": _meihua_stage_profile(
            "original",
            snapshot.upper_trigram,
            snapshot.lower_trigram,
            original,
            deep,
            trigrams,
        ),
        "mutual": _meihua_stage_profile(
            "mutual",
            snapshot.mutual_upper_trigram,
            snapshot.mutual_lower_trigram,
            mutual,
            deep,
            trigrams,
        ),
        "changed": _meihua_stage_profile(
            "changed",
            snapshot.changed_upper_trigram,
            snapshot.changed_lower_trigram,
            changed,
            deep,
            trigrams,
        ),
        "body_use": {
            "body": snapshot.body_trigram,
            "use": snapshot.use_trigram,
            "relation": snapshot.body_use_relation,
            "relation_detail": body_use,
            "body_season_state": snapshot.body_season_state,
            "strength_detail": strength,
            "mutual_upper_relation_to_body": snapshot.mutual_upper_relation_to_body,
            "mutual_lower_relation_to_body": snapshot.mutual_lower_relation_to_body,
            "changed_use_relation_to_body": snapshot.changed_use_relation_to_body,
        },
        "moving_line": {
            "line": snapshot.moving_line,
            **line,
        },
        "football_dimensions": deep["football_dimensions"],
        "ai_rule": deep["ai_rule"],
    }


def meihua_context(snapshot: MeihuaSnapshot) -> list[dict[str, Any]]:
    trigrams = _load_json("meihua_trigrams.json").get("trigrams", [])
    rules = _load_json("meihua_rules.json")
    line_roles = _load_json("meihua_line_roles.json").get("line_roles", [])
    deep = _load_json("meihua_deep_layers.json")

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
        },
        {
            "kind": "meihua_deep_reading_policy",
            "schema_version": deep.get("schema_version"),
            "hexagram_roles": deep.get("hexagram_roles"),
            "upper_lower_roles": deep.get("upper_lower_roles"),
            "football_dimensions": deep.get("football_dimensions"),
            "ai_rule": deep.get("ai_rule"),
        },
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
    context.append(_meihua_deep_profile(snapshot, original, mutual, changed, trigrams))
    return context


def vault_stats() -> dict[str, int]:
    qimen = _qimen_base_rows()
    qimen_deep = _load_json("qimen_deep_layers.json")
    meihua_deep = _load_json("meihua_deep_layers.json")
    return {
        "qimen_palaces": len(qimen["palaces"]),
        "qimen_doors": len(qimen["doors"]),
        "qimen_stars": len(qimen["stars"]),
        "qimen_deities": len(qimen["deities"]),
        "qimen_stems": len(qimen["stems"]),
        "qimen_patterns": len(_qimen_pattern_rows()),
        "qimen_relations": len(all_relations()),
        "qimen_deep_layers": len(qimen_deep.get("reading_hierarchy", [])),
        "qimen_deity_modulations": len(qimen_deep.get("deity_modulation", {})),
        "meihua_trigrams": len(_load_json("meihua_trigrams.json").get("trigrams", [])),
        "meihua_hexagrams": len(_load_json("meihua_hexagrams.json").get("hexagrams", [])),
        "meihua_body_use_relations": len(_load_json("meihua_rules.json").get("body_use_relations", [])),
        "meihua_line_roles": len(_load_json("meihua_line_roles.json").get("line_roles", [])),
        "meihua_deep_dimensions": len(meihua_deep.get("football_dimensions", [])),
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
    relation_rows = (row.to_dict() for row in all_relations())
    _search_rows(results, "QIMEN_DUNJIA", "relations", relation_rows, term)

    qimen_deep = _load_json("qimen_deep_layers.json")
    _search_rows(results, "QIMEN_DUNJIA", "deep:hierarchy", qimen_deep.get("reading_hierarchy", []), term)
    _search_rows(
        results,
        "QIMEN_DUNJIA",
        "deep:deity_modulation",
        ({"key": key, **value} for key, value in qimen_deep.get("deity_modulation", {}).items()),
        term,
    )
    _search_rows(
        results,
        "QIMEN_DUNJIA",
        "deep:state_modifiers",
        ({"key": key, **value} for key, value in qimen_deep.get("state_modifiers", {}).items()),
        term,
    )
    _search_rows(results, "QIMEN_DUNJIA", "deep:football_dimensions", qimen_deep.get("football_dimensions", []), term)

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
    meihua_deep = _load_json("meihua_deep_layers.json")
    _search_rows(
        results,
        "MEIHUA_YISHU",
        "deep:hexagram_roles",
        ({"key": key, **value} for key, value in meihua_deep.get("hexagram_roles", {}).items()),
        term,
    )
    _search_rows(
        results,
        "MEIHUA_YISHU",
        "deep:body_use",
        ({"key": key, **value} for key, value in meihua_deep.get("body_use_principles", {}).items()),
        term,
    )
    _search_rows(
        results,
        "MEIHUA_YISHU",
        "deep:moving_line",
        ({"key": key, **value} for key, value in meihua_deep.get("moving_line_depth", {}).items()),
        term,
    )
    _search_rows(results, "MEIHUA_YISHU", "deep:football_dimensions", meihua_deep.get("football_dimensions", []), term)
    return results[:100]
