from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE = ROOT / "knowledge"
TRIGRAMS = {"乾", "兌", "離", "震", "巽", "坎", "艮", "坤"}
BODY_USE = {"生體", "體生用", "克體", "體克用", "比和"}


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

    trigrams = load("meihua_trigrams.json").get("trigrams", [])
    names = {row.get("name") for row in trigrams}
    require(len(trigrams) == 8 and names == TRIGRAMS, "Meihua trigram catalog must contain exactly all 8 trigrams")
    for row in trigrams:
        for field in ("number", "symbol", "element", "core", "football"):
            require(row.get(field) not in (None, ""), f"Meihua trigram {row.get('name')} missing {field}")

    hexagrams_payload = load("meihua_hexagrams.json")
    require(hexagrams_payload.get("football_status") == "modern_application_not_classical_text", "hexagram football layer must be labeled modern application")
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

    sources = load("sources.json")
    source_ids = {row.get("id") for row in sources.get("sources", [])}
    required_sources = {
        "dunjia-yanyi",
        "qimen-daquan",
        "meihua-yishu-wikisource",
        "zhouyi-wikisource",
        "ctext-book-of-changes",
        "project-football-ontology",
        "project-reading-protocol",
    }
    require(required_sources <= source_ids, "source registry is missing Operation STARK primary sources")

    print(
        "knowledge validation passed: "
        f"Qimen 9 palaces / 8 doors / 9 stars / 8 deities / {len(patterns)} patterns; "
        "Meihua 8 trigrams / 64 hexagrams / 5 body-use relations / 6 moving-line roles"
    )


if __name__ == "__main__":
    main()
