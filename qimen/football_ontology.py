from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from functools import lru_cache
from typing import Any, Iterable

from .constants import (
    DOOR_ELEMENT,
    ELEMENT_CONTROLS,
    ELEMENT_GENERATES,
    PALACES,
    STAR_ELEMENT,
    STEM_ELEMENT,
)
from .knowledge import load_knowledge


MAPPING_SECTIONS = (
    "palaces",
    "doors",
    "stars",
    "deities",
    "stems",
    "branches",
    "seasonal_states",
    "structural_states",
    "patterns",
)

SECTION_LABELS = {
    "palaces": "九宮",
    "doors": "八門",
    "stars": "九星",
    "deities": "八神",
    "stems": "天干",
    "branches": "地支",
    "seasonal_states": "旺衰",
    "structural_states": "結構狀態",
    "patterns": "格局",
}


@dataclass(frozen=True)
class CompositeFootballMeaning:
    mapping_version: str
    symbols: tuple[str, ...]
    dimension_ids: tuple[str, ...]
    football_dimensions: tuple[str, ...]
    layer_readings: tuple[str, ...]
    observable_signals: tuple[str, ...]
    counter_signals: tuple[str, ...]
    interactions: tuple[str, ...]
    confidence: str
    provenance: tuple[str, ...]
    boundary: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@lru_cache(maxsize=1)
def load_football_ontology() -> dict[str, Any]:
    """Return the immutable, versioned football application ontology."""

    return load_knowledge()["files"]["football_ontology.json"]


@lru_cache(maxsize=1)
def _mapping_index() -> dict[str, dict[str, dict[str, Any]]]:
    ontology = load_football_ontology()
    return {
        section: {item["key"]: item for item in ontology["mappings"][section]}
        for section in MAPPING_SECTIONS
    }


def football_dimensions() -> tuple[dict[str, Any], ...]:
    return tuple(load_football_ontology()["dimensions"])


def football_ontology_stats() -> dict[str, Any]:
    ontology = load_football_ontology()
    coverage = ontology["coverage_contract"]
    return {
        "mapping_version": ontology["mapping_version"],
        "dimensions": len(ontology["dimensions"]),
        "atomic_units": sum(len(items) for items in ontology["mappings"].values()),
        "core_combinations": coverage["core_combinations"],
        "visible_stem_extended_combinations": coverage["visible_stem_extended_combinations"],
        "breakdown": dict(coverage["breakdown"]),
        "claim_boundary": coverage["claim_boundary"],
    }


def search_football_meanings(
    query: str = "",
    *,
    dimension: str | None = None,
    section: str | None = None,
) -> list[dict[str, Any]]:
    """Search atomic mappings by symbol, football term, alias or event tag."""

    ontology = load_football_ontology()
    dimension_by_id = {item["id"]: item for item in ontology["dimensions"]}
    normalized = query.strip().casefold()
    results: list[dict[str, Any]] = []
    for current_section in MAPPING_SECTIONS:
        if section and section != current_section:
            continue
        for item in ontology["mappings"][current_section]:
            if dimension and dimension not in item["dimensions"]:
                continue
            searchable = {
                **item,
                "dimension_details": [dimension_by_id[key] for key in item["dimensions"]],
                "section_label": SECTION_LABELS[current_section],
            }
            if normalized and normalized not in _json_text(searchable).casefold():
                continue
            results.append({
                **item,
                "section": current_section,
                "section_label": SECTION_LABELS[current_section],
                "dimension_names": [dimension_by_id[key]["name"] for key in item["dimensions"]],
            })
    return results


def compose_football_meaning(
    *,
    palace: int | str,
    door: str | None = None,
    stars: str | Iterable[str] = (),
    deity: str | None = None,
    heaven_stems: str | Iterable[str] = (),
    earth_stem: str | None = None,
    branches: str | Iterable[str] = (),
    seasonal_state: str | None = None,
    states: Iterable[str] = (),
    patterns: Iterable[str] = (),
) -> CompositeFootballMeaning:
    """Compose every supplied Qimen layer into testable football hypotheses.

    The function is deterministic and total for every valid core
    palace/door/star/deity combination.  It does not assign outcome probability.
    """

    ontology = load_football_ontology()
    indexes = _mapping_index()
    palace_name = _palace_name(palace)
    selected: list[tuple[str, str, str, dict[str, Any]]] = []

    _append_mapping(selected, indexes, "palaces", palace_name, "宮位環境")
    if door:
        _append_mapping(selected, indexes, "doors", door, "八門行動")
    star_names = _as_tuple(stars)
    for star in star_names:
        _append_mapping(selected, indexes, "stars", star, "九星能力")
    if deity:
        _append_mapping(selected, indexes, "deities", deity, "八神表現")
    heaven_names = _as_tuple(heaven_stems)
    for stem in heaven_names:
        _append_mapping(selected, indexes, "stems", stem, "天盤干觸發")
    if earth_stem:
        _append_mapping(selected, indexes, "stems", earth_stem, "地盤干底層")
    for branch in _as_tuple(branches):
        _append_mapping(selected, indexes, "branches", branch, "地支時空")
    if seasonal_state:
        _append_mapping(selected, indexes, "seasonal_states", seasonal_state, "季節旺衰")
    for state in dict.fromkeys(states):
        _append_mapping(selected, indexes, "structural_states", state, "結構修飾")
    for pattern in dict.fromkeys(patterns):
        canonical = _canonical_pattern(pattern)
        _append_mapping(selected, indexes, "patterns", canonical, "格局修飾")

    dimension_counts: Counter[str] = Counter()
    layer_readings: list[str] = []
    observable_signals: list[str] = []
    counter_signals: list[str] = []
    symbols: list[str] = []
    for _section, key, layer, item in selected:
        symbols.append(f"{layer}：{key}")
        dimension_counts.update(item["dimensions"])
        layer_readings.extend(f"{layer}（{key}）：{meaning}" for meaning in item["possible_meanings"])
        observable_signals.extend(item["observable_signals"])
        counter_signals.extend(item["counter_signals"])

    dimension_meta = {item["id"]: item for item in ontology["dimensions"]}
    ontology_order = {item["id"]: index for index, item in enumerate(ontology["dimensions"])}
    dimension_ids = tuple(sorted(
        dimension_counts,
        key=lambda key: (-dimension_counts[key], ontology_order[key]),
    ))
    football_dimension_names = tuple(
        f"{dimension_meta[key]['name']}（{dimension_counts[key]} 層）"
        for key in dimension_ids
    )

    interactions = _element_interactions(
        palace_name=palace_name,
        door=door,
        stars=star_names,
        heaven_stems=heaven_names,
        earth_stem=earth_stem,
    )
    return CompositeFootballMeaning(
        mapping_version=ontology["mapping_version"],
        symbols=tuple(symbols),
        dimension_ids=dimension_ids,
        football_dimensions=football_dimension_names,
        layer_readings=tuple(dict.fromkeys(layer_readings)),
        observable_signals=tuple(dict.fromkeys(observable_signals)),
        counter_signals=tuple(dict.fromkeys(counter_signals)),
        interactions=interactions,
        confidence="應用假說／待賽前資料驗證",
        provenance=(
            "古典符號與格局原義：entities.json、patterns.json（遁甲演義／奇門遁甲秘笈大全摘要）",
            "足球事件語彙：StatsBomb Open Data、FIFA Football Language、IFAB Laws",
            "符號到足球的對應：本專案 football-semantic-composition-v2.0.0 應用規約",
        ),
        boundary="這是可驗證的候選情境，不是勝負、比分、進球數、機率或投注建議。",
    )


def compose_palace_state(
    state: Any,
    *,
    pattern_names: Iterable[str] = (),
    seasonal_state: str | None = None,
    branch: str | None = None,
) -> CompositeFootballMeaning:
    """Convenience adapter for one ``PalaceState`` without importing models."""

    structural_states: list[str] = []
    if state.is_void:
        structural_states.append("旬空")
    if state.is_horse:
        structural_states.append("驛馬")
    return compose_football_meaning(
        palace=state.number,
        door=state.door,
        stars=state.stars,
        deity=state.deity,
        heaven_stems=state.heaven_stems,
        earth_stem=state.earth_stem,
        branches=(branch,) if branch else (),
        seasonal_state=seasonal_state,
        states=structural_states,
        patterns=pattern_names,
    )


def _append_mapping(
    selected: list[tuple[str, str, str, dict[str, Any]]],
    indexes: dict[str, dict[str, dict[str, Any]]],
    section: str,
    key: str,
    layer: str,
) -> None:
    try:
        selected.append((section, key, layer, indexes[section][key]))
    except KeyError as exc:
        raise ValueError(f"足球語義庫沒有 {SECTION_LABELS[section]}條目：{key}") from exc


def _palace_name(palace: int | str) -> str:
    if isinstance(palace, int):
        try:
            return PALACES[palace]["name"]
        except KeyError as exc:
            raise ValueError(f"宮位必須為 1–9：{palace}") from exc
    if palace.isdigit():
        return _palace_name(int(palace))
    if palace in _mapping_index()["palaces"]:
        return palace
    raise ValueError(f"無法辨識宮位：{palace}")


def _canonical_pattern(name: str) -> str:
    if name in {"星伏吟", "門伏吟"}:
        return "伏吟"
    if name in {"星反吟", "門反吟"}:
        return "反吟"
    return name


def _as_tuple(value: str | Iterable[str]) -> tuple[str, ...]:
    if isinstance(value, str):
        return (value,) if value else ()
    return tuple(value)


def _element_interactions(
    *,
    palace_name: str,
    door: str | None,
    stars: tuple[str, ...],
    heaven_stems: tuple[str, ...],
    earth_stem: str | None,
) -> tuple[str, ...]:
    palace_number = next(number for number, meta in PALACES.items() if meta["name"] == palace_name)
    palace_element = PALACES[palace_number]["element"]
    results: list[str] = []
    if door:
        results.append(_relation_text("宮門", palace_name, palace_element, door, DOOR_ELEMENT[door]))
    for star in stars:
        results.append(_relation_text("星宮", star, STAR_ELEMENT[star], palace_name, palace_element))
        if door:
            results.append(_relation_text("星門", star, STAR_ELEMENT[star], door, DOOR_ELEMENT[door]))
    if earth_stem:
        for heaven_stem in heaven_stems:
            results.append(_relation_text(
                "天地盤干",
                f"天盤{heaven_stem}",
                STEM_ELEMENT[heaven_stem],
                f"地盤{earth_stem}",
                STEM_ELEMENT[earth_stem],
            ))
    return tuple(dict.fromkeys(results))


def _relation_text(label: str, first: str, first_element: str, second: str, second_element: str) -> str:
    if first_element == second_element:
        reading = "同氣，相關行為容易重複或放大，也要防止打法單一化"
    elif ELEMENT_GENERATES[first_element] == second_element:
        reading = f"{first}生{second}，前層為後層提供條件"
    elif ELEMENT_GENERATES[second_element] == first_element:
        reading = f"{second}生{first}，後層反向支援前層但可能消耗自身"
    elif ELEMENT_CONTROLS[first_element] == second_element:
        reading = f"{first}剋{second}，兩層存在直接限制或摩擦"
    else:
        reading = f"{second}剋{first}，前層作用可能受壓、延遲或變形"
    return f"{label}：{first}（{first_element}）與{second}（{second_element}）— {reading}。"


def _json_text(value: Any) -> str:
    import json

    return json.dumps(value, ensure_ascii=False, sort_keys=True)
