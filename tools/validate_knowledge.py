from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from jarvis.qimen_relations import all_relations  # noqa: E402


KNOWLEDGE = ROOT / "knowledge"
TRIGRAMS = {"乾", "兌", "離", "震", "巽", "坎", "艮", "坤"}
BODY_USE = {"生體", "體生用", "克體", "體克用", "比和"}
DEITIES = {"值符", "螣蛇", "太陰", "六合", "白虎", "玄武", "九地", "九天"}


def load(name: str):
    return json.loads((KNOWLEDGE / name).read_text(encoding="utf-8"))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"knowledge validation failed: {message}")


def main() -> None:
    entities = load("entities.json")
    require(len(entities.get("palaces", [])) == 9, "Qimen palaces must be 9")
    require(len(entities.get("doors", [])) == 8, "Qimen doors must be 8")
    require(len(entities.get("stars", [])) == 9, "Qimen stars must be 9")
    require(len(entities.get("deities", [])) == 8, "Qimen deities must be 8")
    require(len(entities.get("stems", [])) == 10, "Qimen stems must be 10")

    patterns = load("patterns.json").get("patterns", [])
    require(patterns, "Qimen pattern catalog must not be empty")
    for row in patterns:
        require(bool(row.get("name")), "every Qimen pattern needs a name")
        require(bool(row.get("reading")), f"Qimen pattern {row.get('name')} needs a reading")
        require(bool(row.get("caution")), f"Qimen pattern {row.get('name')} needs a caution")

    relation_rows = all_relations()
    require(len(relation_rows) == 306, "Qimen Core relation matrix must contain exactly 306 slots")
    require(len({row.key for row in relation_rows}) == 306, "Qimen relation keys must be unique")
    relation_counts = {
        relation_type: sum(row.relation_type == relation_type for row in relation_rows)
        for relation_type in ("stem_pair", "star_door", "door_palace", "star_palace")
    }
    require(
        relation_counts == {"stem_pair": 81, "star_door": 72, "door_palace": 72, "star_palace": 81},
        "Qimen Core 306 family counts are incomplete",
    )
    for row in relation_rows:
        require(bool(row.general_interpretation), f"Qimen relation {row.key} missing general interpretation")
        require(bool(row.football_meaning), f"Qimen relation {row.key} missing football meaning")
        require(bool(row.observable_signals), f"Qimen relation {row.key} missing observable signals")
        require(bool(row.counter_signals), f"Qimen relation {row.key} missing counter signals")

    qimen_deep = load("qimen_deep_layers.json")
    require(len(qimen_deep.get("reading_hierarchy", [])) == 8, "Qimen deep hierarchy must contain 8 layers")
    require(set(qimen_deep.get("deity_modulation", {})) == DEITIES, "Qimen deep deity modulation must cover all 8 deities")
    require(len(qimen_deep.get("football_dimensions", [])) >= 8, "Qimen deep football dimensions are incomplete")
    for name, row in qimen_deep["deity_modulation"].items():
        require(bool(row.get("general")), f"Qimen deity {name} missing deep general meaning")
        require(bool(row.get("football")), f"Qimen deity {name} missing deep football meaning")
        require(bool(row.get("observable")) and bool(row.get("counter")), f"Qimen deity {name} needs evidence and counter-evidence")

    ontology = load("football_ontology.json")
    require(bool(ontology.get("boundaries")), "football ontology needs claim boundaries")
    require(bool(ontology.get("dimensions")), "football ontology needs observable dimensions")
    require(isinstance(ontology.get("mappings"), dict), "football ontology mappings must be an object")
    for family, rows in ontology["mappings"].items():
        if not isinstance(rows, list):
            continue
        for row in rows:
            require(bool(row.get("key")), f"football mapping in {family} needs a key")
            require(bool(row.get("possible_meanings")), f"football mapping {row.get('key')} needs meanings")
            require(bool(row.get("observable_signals")), f"football mapping {row.get('key')} needs observable signals")
            require(bool(row.get("counter_signals")), f"football mapping {row.get('key')} needs counter signals")

    interpretation = load("interpretation.json")
    require(bool(interpretation.get("source_policy")), "Qimen interpretation protocol needs source policy")
    require(bool(interpretation.get("relation_contract")), "Qimen interpretation protocol needs relation contract")

    trigrams = load("meihua_trigrams.json").get("trigrams", [])
    names = {row.get("name") for row in trigrams}
    require(len(trigrams) == 8 and names == TRIGRAMS, "Meihua trigram catalog must contain exactly all 8 trigrams")
    for row in trigrams:
        for field in ("number", "symbol", "element", "core", "classical_correspondences", "football"):
            require(row.get(field) not in (None, ""), f"Meihua trigram {row.get('name')} missing {field}")
        require(bool(row.get("football_observable")), f"Meihua trigram {row.get('name')} missing football observables")
        require(bool(row.get("football_counter")), f"Meihua trigram {row.get('name')} missing football counters")

    hexagrams_payload = load("meihua_hexagrams.json")
    require(
        hexagrams_payload.get("football_status") == "modern_application_not_classical_text",
        "hexagram football layer must be labeled modern application",
    )
    hexagrams = hexagrams_payload.get("hexagrams", [])
    require(len(hexagrams) == 64, "Meihua hexagram catalog must contain 64 entries")
    require({row.get("number") for row in hexagrams} == set(range(1, 65)), "hexagram numbers must be exactly 1..64")
    require(len({row.get("name") for row in hexagrams}) == 64, "hexagram names must be unique")
    require(len({row.get("symbol") for row in hexagrams}) == 64, "hexagram symbols must be unique")
    pairs = {(row.get("upper"), row.get("lower")) for row in hexagrams}
    require(len(pairs) == 64, "all 8x8 upper/lower trigram combinations must appear exactly once")
    require(all(upper in TRIGRAMS and lower in TRIGRAMS for upper, lower in pairs), "hexagrams contain unknown trigrams")
    for row in hexagrams:
        for field in ("theme", "summary", "football"):
            require(bool(row.get(field)), f"hexagram {row.get('name')} missing {field}")

    rules = load("meihua_rules.json")
    relations = {row.get("relation") for row in rules.get("body_use_relations", [])}
    require(relations == BODY_USE, "Meihua body/use catalog must contain exactly 5 relations")
    require(bool(rules.get("interpretation_order")), "Meihua interpretation order must be defined")

    line_roles = load("meihua_line_roles.json").get("line_roles", [])
    require({row.get("line") for row in line_roles} == set(range(1, 7)), "Meihua moving-line roles must cover 1..6")
    for row in line_roles:
        require(bool(row.get("general")) and bool(row.get("football")), "moving-line roles need general and football meanings")

    meihua_deep = load("meihua_deep_layers.json")
    require(set(meihua_deep.get("hexagram_roles", {})) == {"original", "mutual", "changed"}, "Meihua deep profile must define original/mutual/changed roles")
    require(set(meihua_deep.get("body_use_principles", {})) == BODY_USE, "Meihua deep body/use principles must cover all 5 relations")
    require(set(meihua_deep.get("strength_rules", {})) == {"旺", "平", "衰"}, "Meihua deep strength rules must cover 旺平衰")
    require(set(meihua_deep.get("moving_line_depth", {})) == {str(i) for i in range(1, 7)}, "Meihua deep moving-line rules must cover 1..6")
    require(len(meihua_deep.get("football_dimensions", [])) == 8, "Meihua deep football dimensions must contain 8 layers")
    for relation, row in meihua_deep["body_use_principles"].items():
        require(bool(row.get("general")) and bool(row.get("football")), f"Meihua {relation} deep meanings incomplete")
        require(bool(row.get("observe")) and bool(row.get("counter")), f"Meihua {relation} needs evidence and counter-evidence")

    zhouyi_review = load("zhouyi_review_policy.json")
    zhouyi_dimensions = zhouyi_review.get("review_dimensions", [])
    require(len(zhouyi_dimensions) == 10, "Zhouyi method-aware review policy must contain 10 dimensions")
    require(bool(zhouyi_review.get("authority_order")), "Zhouyi review authority order is required")
    require(bool(zhouyi_review.get("ai_review_order")), "Zhouyi AI review order is required")
    method_weighting = zhouyi_review.get("method_weighting_policy", {})
    require(set(method_weighting) == {"XIANTIAN_NUMBER_METHOD", "HOUTIAN_OBJECT_METHOD"}, "Zhouyi method weighting must cover xiantian/houtian")
    require(method_weighting["XIANTIAN_NUMBER_METHOD"].get("zhouyi_role") == "SUPPORTING", "xiantian Zhouyi role must be SUPPORTING")
    require(method_weighting["HOUTIAN_OBJECT_METHOD"].get("zhouyi_role") == "PRIMARY_SUPPORT", "houtian Zhouyi role must be PRIMARY_SUPPORT")
    football_contract = zhouyi_review.get("football_meaning_contract", {})
    require(bool(football_contract.get("required_fields")), "Zhouyi football meaning contract needs required fields")
    require(bool(football_contract.get("forbidden_shortcuts")), "Zhouyi review must list forbidden shortcuts")
    dimension_ids = {dimension.get("id") for dimension in zhouyi_dimensions}
    require("method_fidelity" in dimension_ids, "Zhouyi review must include method fidelity")
    require("external_response" in dimension_ids, "Zhouyi review must include external-response audit")
    for dimension in zhouyi_dimensions:
        require(bool(dimension.get("id")) and bool(dimension.get("name")), "Zhouyi review dimension needs id/name")
        require(bool(dimension.get("questions")), f"Zhouyi review dimension {dimension.get('id')} needs questions")
        require(bool(dimension.get("football_rule")), f"Zhouyi review dimension {dimension.get('id')} needs football boundary")

    sources = load("sources.json")
    source_ids = {row.get("id") for row in sources.get("sources", [])}
    required_sources = {
        "dunjia-yanyi",
        "qimen-daquan",
        "meihua-yishu-wikisource",
        "zhouyi-wikisource",
        "zhouyi-kanripo-tls-transcription",
        "ctext-book-of-changes",
        "yilin-kanripo-wyg-transcription",
        "project-football-ontology",
        "project-reading-protocol",
        "liuyao-zengshan-buyi",
        "liuyao-bosizhengzong",
        "liuyao-huozhulin",
        "liuyao-huangjince",
    }
    require(required_sources <= source_ids, "source registry is missing Operation STARK primary sources")

    print(
        "knowledge validation passed: "
        f"Qimen 9 palaces / 8 doors / 9 stars / 8 deities / 10 stems / {len(patterns)} patterns / "
        "Core 306 relations / 8 deep hierarchy layers / 8 deity modulations; "
        "Meihua 8 trigrams / 64 hexagrams / 5 body-use relations / 6 moving-line roles / 8 deep football dimensions; "
        "Zhouyi 10 method-aware source-review dimensions; "
        "Liuyao 4 classical source anchors"
    )


if __name__ == "__main__":
    main()
