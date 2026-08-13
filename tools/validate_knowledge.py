from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from qimen.constants import SOLAR_TERM_JU  # noqa: E402
from qimen.football_ontology import football_ontology_stats  # noqa: E402
from qimen.interpretation import interpretation_stats  # noqa: E402
from qimen.knowledge import KNOWLEDGE_FILES, load_knowledge  # noqa: E402


def require_unique(items, key, label):
    values = [item[key] for item in items]
    if len(values) != len(set(values)):
        raise AssertionError(f"{label} 有重複 {key}")


def main() -> int:
    data = load_knowledge()["files"]
    for filename in KNOWLEDGE_FILES:
        path = ROOT / "knowledge" / filename
        json.loads(path.read_text(encoding="utf-8"))
        if not data[filename]["schema_version"].startswith("qimen-"):
            raise AssertionError(f"{filename} 缺少 qimen schema 版本")

    entities = data["entities.json"]
    expected = {"palaces": 9, "doors": 8, "stars": 9, "deities": 8, "stems": 10}
    for section, count in expected.items():
        if len(entities[section]) != count:
            raise AssertionError(f"{section} 應有 {count} 筆")
        require_unique(entities[section], "key", section)

    calendar = data["calendar.json"]
    require_unique(calendar["solar_terms"], "name", "solar_terms")
    require_unique(calendar["earthly_branches"], "name", "earthly_branches")
    knowledge_ju = {item["name"]: tuple(item["ju"]) for item in calendar["solar_terms"]}
    if knowledge_ju != SOLAR_TERM_JU:
        raise AssertionError("calendar.json 十八局表與引擎常數不一致")

    sources = {item["id"] for item in data["sources.json"]["sources"]}
    patterns = data["patterns.json"]["patterns"]
    require_unique(patterns, "name", "patterns")
    for item in patterns:
        for field in ("category", "condition", "reading", "caution", "automation", "source_id"):
            if not item.get(field):
                raise AssertionError(f"格局 {item['name']} 缺少 {field}")
        if item["automation"] not in {"implemented", "knowledge_only"}:
            raise AssertionError(f"格局 {item['name']} automation 無效")
        if item["source_id"] not in sources:
            raise AssertionError(f"格局 {item['name']} 來源不存在")

    ontology = data["football_ontology.json"]
    expected_mappings = {
        "palaces": 9,
        "doors": 8,
        "stars": 9,
        "deities": 8,
        "stems": 10,
        "branches": 12,
        "seasonal_states": 5,
        "structural_states": 8,
        "patterns": len(patterns),
    }
    dimensions = {item["id"] for item in ontology["dimensions"]}
    for section, count in expected_mappings.items():
        mappings = ontology["mappings"][section]
        if len(mappings) != count:
            raise AssertionError(f"football {section} 應有 {count} 筆")
        require_unique(mappings, "key", f"football {section}")
        for item in mappings:
            if not set(item["dimensions"]).issubset(dimensions):
                raise AssertionError(f"足球義 {item['key']} 使用不存在的維度")
            for field in ("possible_meanings", "observable_signals", "counter_signals"):
                if not item.get(field):
                    raise AssertionError(f"足球義 {item['key']} 缺少 {field}")
    dimension_sources = {
        source_id
        for item in ontology["dimensions"]
        for source_id in item["source_ids"]
    }
    if not dimension_sources.issubset(sources):
        raise AssertionError(f"足球維度來源不存在：{sorted(dimension_sources - sources)}")
    stats = football_ontology_stats()
    if stats["atomic_units"] != ontology["coverage_contract"]["mapped_atomic_units"]:
        raise AssertionError("足球義原子條目數與 coverage_contract 不一致")

    interpretation = data["interpretation.json"]
    interpretation_sections = (
        "precast_checklist",
        "reading_layers",
        "classic_principles",
        "role_models",
        "focus_topics",
        "timing_rules",
        "time_basis_options",
        "external_evidence_protocol",
        "error_traps",
    )
    for section in interpretation_sections:
        items = interpretation[section]
        require_unique(items, "id", section)
        for item in items:
            if not item.get("source_ids"):
                raise AssertionError(f"解盤條目 {item['id']} 缺少 source_ids")
            unknown_sources = set(item["source_ids"]) - sources
            if unknown_sources:
                raise AssertionError(f"解盤條目 {item['id']} 來源不存在：{sorted(unknown_sources)}")
    reading_stats = interpretation_stats()
    contract = interpretation["relation_contract"]
    if reading_stats["total_relations"] != contract["total_relations"]:
        raise AssertionError("解盤關係矩陣與 relation_contract 不一致")
    expected_relations = {
        "stem_pair": contract["visible_stem_pairs"],
        "star_door": contract["star_door_pairs"],
        "door_palace": contract["door_palace_pairs"],
        "star_palace": contract["star_palace_pairs"],
    }
    if reading_stats["relation_counts"] != expected_relations:
        raise AssertionError("解盤關係類型筆數不完整")

    print(
        f"OK: {sum(len(v) for v in entities.values() if isinstance(v, list))} 個核心實體、"
        f"{len(patterns)} 個格局、24 節氣、{stats['atomic_units']} 個足球義單元、"
        f"{stats['core_combinations']:,} 個核心組合、{reading_stats['total_relations']} 組解盤關係。"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
