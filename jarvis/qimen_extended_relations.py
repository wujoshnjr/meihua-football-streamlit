from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from qimen.constants import DEITIES, DOOR_ELEMENT, PALACES, STAR_ELEMENT, STEM_ELEMENT, STEMS
from qimen.models import PalaceState


ROOT = Path(__file__).resolve().parents[1]
ENTITIES_PATH = ROOT / "knowledge" / "entities.json"
DOORS = tuple(DOOR_ELEMENT)
STARS = tuple(STAR_ELEMENT)
PALACE_NAMES = tuple(PALACES[number]["name"] for number in sorted(PALACES))
AUTHORITY = "PROJECT_HEURISTIC__COMPONENTS_SOURCE_BACKED"


def _element_relation(left: str, right: str) -> str:
    generates = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
    controls = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}
    if left == right:
        return "SAME_ELEMENT"
    if generates[left] == right:
        return "LEFT_GENERATES_RIGHT"
    if generates[right] == left:
        return "RIGHT_GENERATES_LEFT"
    if controls[left] == right:
        return "LEFT_CONTROLS_RIGHT"
    return "RIGHT_CONTROLS_LEFT"


@lru_cache(maxsize=1)
def _entities() -> dict[str, dict[str, dict[str, Any]]]:
    payload = json.loads(ENTITIES_PATH.read_text(encoding="utf-8"))
    result: dict[str, dict[str, dict[str, Any]]] = {}
    for family in ("palaces", "doors", "stars", "deities", "stems"):
        rows = payload.get(family, [])
        result[family] = {
            str(row.get("key") or row.get("name")): row
            for row in rows
            if row.get("key") or row.get("name")
        }
    return result


def _row(family: str, key: str) -> dict[str, Any]:
    return _entities().get(family, {}).get(key, {"key": key})


def _keywords(row: dict[str, Any]) -> list[str]:
    raw = row.get("keywords") or []
    return [str(item) for item in raw if item]


def _football(row: dict[str, Any], fallback: str) -> str:
    return str(row.get("football") or fallback)


def _component_basis(family: str, key: str) -> dict[str, str]:
    return {
        "source": "knowledge/entities.json",
        "family": family,
        "key": key,
        "authority": "PROJECT_KNOWLEDGE_COMPONENT",
    }


def _football_application(
    *,
    left: str,
    right: str,
    left_football: str,
    right_football: str,
    condition_note: str,
) -> dict[str, Any]:
    return {
        "source_basis": [
            f"{left} component meaning from JARVIS entity/deep knowledge",
            f"{right} component meaning from JARVIS entity/deep knowledge",
        ],
        "abstract_meaning": f"把 {left} 與 {right} 視為同宮共現的條件組合，而不是兩個符號加分。",
        "possible_scenario": f"{left_football}；同時 {right_football}。{condition_note}",
        "observable_signals": [
            f"場上同時出現可對應 {left} 與 {right} 的可觀察行為",
            "該宮代表的功能在比賽中持續、重複而非只出現一次偶發現象",
        ],
        "counter_signals": [
            f"只有 {left} 的表象、但 {right} 所代表功能沒有實際落地",
            f"只有 {right} 的表象、但 {left} 的調制方式不成立",
            "旬空、門迫、入墓、擊刑或其他更高權重 modifier 明顯削弱此組合",
        ],
        "confidence_note": "這是現代足球條件式映射；需和用神、旺衰、空馬、格局與同宮其他層一起讀，不能獨立生成勝負或比分。",
    }


def _relation(
    *,
    key: str,
    family: str,
    objects: list[dict[str, Any]],
    source_basis: list[dict[str, str]],
    general_interpretation: str,
    conditions: list[str],
    observable_signals: list[str],
    counter_signals: list[str],
    football_modern_application: dict[str, Any],
    element_relation: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "key": key,
        "family": family,
        "objects": objects,
        "source_basis": source_basis,
        "general_interpretation": general_interpretation,
        "conditions": conditions,
        "observable_signals": observable_signals,
        "counter_signals": counter_signals,
        "football_modern_application": football_modern_application,
        "authority": AUTHORITY,
        "caution": (
            "組合層沒有被宣稱為古籍逐條原文。先保留各元件與盤面事實，再由 ChatGPT 做條件式合參；"
            "禁止符號投票、固定比分、機率與賽後回填。"
        ),
    }
    if element_relation:
        payload["element_relation"] = element_relation
    return payload


def _deity_door(deity: str, door: str) -> dict[str, Any]:
    deity_row = _row("deities", deity)
    door_row = _row("doors", door)
    return _relation(
        key=f"deity_x_door:{deity}:{door}",
        family="deity_x_door",
        objects=[{"role": "deity", "name": deity}, {"role": "door", "name": door}],
        source_basis=[_component_basis("deities", deity), _component_basis("doors", door)],
        general_interpretation=(
            f"以{deity}作為顯化／心理／可信度調制層，閱讀{door}所代表的行動通道。"
            "神不取代門，門也不反向決定神的吉凶。"
        ),
        conditions=["同宮實際共現", "先判用神是否落此宮", "再審旬空、門迫、旺衰與特殊格局"],
        observable_signals=[f"{deity}關鍵詞：{'、'.join(_keywords(deity_row)) or '依 entity 定義'}", f"{door}關鍵詞：{'、'.join(_keywords(door_row)) or '依 entity 定義'}"],
        counter_signals=["只有單一元件可被觀察，另一元件的條件沒有落實", "更高權重盤面條件直接限制門的實際可用性"],
        football_modern_application=_football_application(
            left=deity,
            right=door,
            left_football=_football(deity_row, f"觀察{deity}的調制方式"),
            right_football=_football(door_row, f"觀察{door}的行動通道"),
            condition_note="重點是『行動如何被調制』，不是吉神吉門相加。",
        ),
    )


def _deity_star(deity: str, star: str) -> dict[str, Any]:
    deity_row = _row("deities", deity)
    star_row = _row("stars", star)
    return _relation(
        key=f"deity_x_star:{deity}:{star}",
        family="deity_x_star",
        objects=[{"role": "deity", "name": deity}, {"role": "star", "name": star}],
        source_basis=[_component_basis("deities", deity), _component_basis("stars", star)],
        general_interpretation=f"以{deity}調制{star}所代表的能力、組織品質與事件顯化方式；不得以吉／凶標籤直接相乘。",
        conditions=["同宮實際共現", "區分用神宮與背景宮", "和門、宮、天地盤干及 modifier 同讀"],
        observable_signals=[f"{deity}關鍵詞：{'、'.join(_keywords(deity_row)) or '依 entity 定義'}", f"{star}關鍵詞：{'、'.join(_keywords(star_row)) or '依 entity 定義'}"],
        counter_signals=["星的能力未在場上形成持續行為", "神的調制特徵沒有任何可驗證表現"],
        football_modern_application=_football_application(
            left=deity,
            right=star,
            left_football=_football(deity_row, f"觀察{deity}的調制方式"),
            right_football=_football(star_row, f"觀察{star}的能力表現"),
            condition_note="重點是能力以何種方式顯化、被放大、隱藏、連結或干擾。",
        ),
    )


def _deity_palace(deity: str, palace_number: int) -> dict[str, Any]:
    palace_name = PALACES[palace_number]["name"]
    deity_row = _row("deities", deity)
    palace_row = _row("palaces", palace_name)
    return _relation(
        key=f"deity_x_palace:{deity}:{palace_number}",
        family="deity_x_palace",
        objects=[{"role": "deity", "name": deity}, {"role": "palace", "number": palace_number, "name": palace_name}],
        source_basis=[_component_basis("deities", deity), _component_basis("palaces", palace_name)],
        general_interpretation=f"把{deity}的調制方式放入{palace_name}的環境、方位與五行條件中閱讀；宮是環境，神是顯化修飾。",
        conditions=["同宮實際共現", "宮位旺衰與旬空／驛馬必須共同審查", "中五宮必須遵守既定寄宮政策"],
        observable_signals=[f"{deity}關鍵詞：{'、'.join(_keywords(deity_row)) or '依 entity 定義'}", f"{palace_name}環境：{palace_row.get('image') or PALACES[palace_number]['element']}"],
        counter_signals=["環境功能與神的顯化方向明顯脫節", "此宮受空、墓、迫等條件使訊號無法落實"],
        football_modern_application=_football_application(
            left=deity,
            right=palace_name,
            left_football=_football(deity_row, f"觀察{deity}的調制方式"),
            right_football=_football(palace_row, f"觀察{palace_name}代表的比賽環境"),
            condition_note="先判宮是否為主客核心用神宮，再決定此組合的實際閱讀權重。",
        ),
    )


def _stem_door(stem: str, door: str) -> dict[str, Any]:
    stem_row = _row("stems", stem)
    door_row = _row("doors", door)
    relation = _element_relation(STEM_ELEMENT[stem], DOOR_ELEMENT[door])
    return _relation(
        key=f"stem_x_door:{stem}:{door}",
        family="stem_x_door",
        objects=[{"role": "stem", "name": stem, "element": STEM_ELEMENT[stem]}, {"role": "door", "name": door, "element": DOOR_ELEMENT[door]}],
        source_basis=[_component_basis("stems", stem), _component_basis("doors", door)],
        general_interpretation=f"閱讀{stem}作為人物／觸發條件時，與{door}行動通道之間的可行性、資源流向與受制關係；五行關係={relation}。",
        conditions=["先確認此干在盤中的天盤／地盤角色", "若是主客用神須提高權重，背景干不得同權", "與天地盤干格局、門迫及旺衰合讀"],
        observable_signals=[f"{stem}：{stem_row.get('football') or stem_row.get('image') or '依天干知識層'}", f"{door}：{_football(door_row, '依門義觀察行動通道')}"],
        counter_signals=["干所代表的人／條件並非本題核心", "門的功能被空亡、迫制或其他強條件削弱"],
        football_modern_application=_football_application(
            left=stem,
            right=door,
            left_football=_football(stem_row, f"觀察{stem}作為用神／觸發條件"),
            right_football=_football(door_row, f"觀察{door}的實際通道"),
            condition_note=f"五行關係 {relation} 只是條件，不是自動強弱分數。",
        ),
        element_relation=relation,
    )


def _stem_star(stem: str, star: str) -> dict[str, Any]:
    stem_row = _row("stems", stem)
    star_row = _row("stars", star)
    relation = _element_relation(STEM_ELEMENT[stem], STAR_ELEMENT[star])
    return _relation(
        key=f"stem_x_star:{stem}:{star}",
        family="stem_x_star",
        objects=[{"role": "stem", "name": stem, "element": STEM_ELEMENT[stem]}, {"role": "star", "name": star, "element": STAR_ELEMENT[star]}],
        source_basis=[_component_basis("stems", stem), _component_basis("stars", star)],
        general_interpretation=f"閱讀{stem}所代表的人／觸發條件與{star}能力品質之間的配合、消耗或制約；五行關係={relation}。",
        conditions=["先確認干是否為主客用神或關鍵天盤干", "星的能力需經門與宮檢查是否可落地", "天禽隨天芮時保留雙星事實，不重複加分"],
        observable_signals=[f"{stem}：{stem_row.get('football') or stem_row.get('image') or '依天干知識層'}", f"{star}：{_football(star_row, '依星義觀察能力品質')}"],
        counter_signals=["干不是本題核心而只是背景", "星的能力被宮門／空墓迫制明顯削弱"],
        football_modern_application=_football_application(
            left=stem,
            right=star,
            left_football=_football(stem_row, f"觀察{stem}的觸發／用神角色"),
            right_football=_football(star_row, f"觀察{star}的能力表現"),
            condition_note=f"五行關係 {relation} 用來描述條件方向，不作符號投票。",
        ),
        element_relation=relation,
    )


@lru_cache(maxsize=1)
def all_extended_relations() -> tuple[dict[str, Any], ...]:
    rows: list[dict[str, Any]] = []
    rows.extend(_deity_door(deity, door) for deity in DEITIES for door in DOORS)
    rows.extend(_deity_star(deity, star) for deity in DEITIES for star in STARS)
    rows.extend(_deity_palace(deity, number) for deity in DEITIES for number in sorted(PALACES))
    rows.extend(_stem_door(stem, door) for stem in STEMS for door in DOORS)
    rows.extend(_stem_star(stem, star) for stem in STEMS for star in STARS)
    return tuple(rows)


@lru_cache(maxsize=1)
def _by_key() -> dict[str, dict[str, Any]]:
    return {row["key"]: row for row in all_extended_relations()}


def extended_relations_for_palace(state: PalaceState) -> list[dict[str, Any]]:
    keys: list[str] = []
    if state.deity and state.door:
        keys.append(f"deity_x_door:{state.deity}:{state.door}")
    if state.deity:
        keys.append(f"deity_x_palace:{state.deity}:{state.number}")
        keys.extend(f"deity_x_star:{state.deity}:{star}" for star in state.stars)
    if state.door:
        keys.extend(f"stem_x_door:{stem}:{state.door}" for stem in state.heaven_stems)
    keys.extend(f"stem_x_star:{stem}:{star}" for stem in state.heaven_stems for star in state.stars)
    index = _by_key()
    return [index[key] for key in keys if key in index]


def extended_relation_audit() -> dict[str, Any]:
    rows = all_extended_relations()
    families = {
        family: sum(row["family"] == family for row in rows)
        for family in ("deity_x_door", "deity_x_star", "deity_x_palace", "stem_x_door", "stem_x_star")
    }
    return {
        "schema_version": "stark-qimen-extended-relation-audit-v1.0.0",
        "total": len(rows),
        "families": families,
        "unique_keys": len({row["key"] for row in rows}),
        "authority": AUTHORITY,
        "dynamic_modifier_stack": "MATERIALIZED_AT_CHART_RUNTIME",
        "boundary": "378 個靜態組合是 project review materialization，不等於『所有奇門關係』；state modifiers 依實際盤面動態疊加。",
    }
