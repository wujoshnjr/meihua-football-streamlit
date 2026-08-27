from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from jarvis.yuanling_vault import casting_reference, search_yuanling, yuanling_catalog_stats  # noqa: E402


KNOWLEDGE = ROOT / "knowledge"


def load(name: str) -> dict:
    return json.loads((KNOWLEDGE / name).read_text(encoding="utf-8"))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"Expanded Yuanling validation failed: {message}")


def main() -> None:
    extended = load("yuanling_extended_source_catalog.json")
    work_index = load("yuanling_work_index.json")
    reference = load("yuanling_casting_reference.json")

    require(
        extended.get("schema_version") == "stark-yuanling-extended-source-catalog-v1.0.0",
        "extended catalog schema drift",
    )
    sections = extended.get("sections", [])
    require(len(sections) == 9, "extended catalog must contain nine reviewed sections")
    by_id = {row["id"]: row for row in sections}
    require(len(by_id) == 9, "extended source ids must be unique")

    cutoff = by_id["yuanling.vol1.cutoff_void"]["machine_facts"]
    require(cutoff["甲"] == ["申", "酉"] and cutoff["癸"] == ["子", "丑"], "cutoff-void anchors drift")
    require(len(by_id["yuanling.vol1.eight_trigram_origins"]["machine_facts"]) == 9, "nine-palace source profile incomplete")
    require(len(by_id["yuanling.vol2.eight_doors_affairs"]["machine_facts"]) == 8, "eight-door source profile incomplete")
    require(len(by_id["yuanling.vol2.nine_palace_chief_profiles"]["machine_facts"]) == 9, "palace chief profile incomplete")
    require(len(by_id["yuanling.vol2.ten_stem_judgments"]["machine_facts"]) == 10, "ten-stem source profile incomplete")
    require(
        by_id["yuanling.vol2.nine_dun_and_fraud_patterns"]["machine_facts"]["enumeration_status"]
        == "SOURCE_REVIEW_REQUIRED_BEFORE_CLAIMING_EXACT_NINE",
        "nine-dun uncertainty was hidden",
    )
    require(
        by_id["yuanling.vol2.heaven_earth_stem_pairs"]["machine_facts"]["materialization_status"]
        == "SECTION_INDEXED__FULL_PAIR_TEXT_NOT_YET_MATERIALIZED_IN_YUANLING_CATALOG",
        "stem-pair source corpus must not be overstated",
    )
    require(len(by_id["yuanling.vol3.shortcut_numeric_star_door"]["machine_facts"]) == 9, "shortcut numeric-star profiles incomplete")
    require(len(by_id["yuanling.vol3.nine_star_response"]["machine_facts"]) == 9, "nine-star response profiles incomplete")

    require(
        work_index.get("schema_version") == "stark-yuanling-work-index-v1.0.0",
        "work index schema drift",
    )
    volumes = work_index.get("volumes", [])
    require([row["volume"] for row in volumes] == list(range(1, 25)), "work index must cover volumes 1..24 exactly")
    volume24 = volumes[-1]
    require("占勝敗" in volume24["chapters"], "volume 24 competition chapter missing")
    require(work_index["coverage"]["full_rule_materialization_complete"] is False, "TOC index must not claim full rule materialization")

    require(
        reference.get("schema_version") == "stark-yuanling-casting-reference-v1.1.0",
        "casting reference schema drift",
    )
    methods = {row["id"]: row for row in reference.get("methods", [])}
    require(
        set(methods) == {"YUANLING_QIMEN_CASTING_REFERENCE", "YUANLING_YANSHU_QIYAO_RAW", "YUANLING_RI_QIMEN"},
        "casting reference must keep the three Yuanling method identities separate",
    )
    require(methods["YUANLING_QIMEN_CASTING_REFERENCE"]["status"] == "SOURCE_REFERENCE_NOT_SEPARATE_PRODUCTION_ENGINE", "source casting reference status drift")
    require(methods["YUANLING_RI_QIMEN"]["status"] == "SOURCE_CROSSCHECKED_RECONSTRUCTION_ALPHA", "Ri-Qimen crosschecked reconstruction status drift")
    require("數宮" in methods["YUANLING_YANSHU_QIYAO_RAW"]["seven_factors"], "Qiyao factors missing")

    stats = yuanling_catalog_stats()
    require(stats["structured_sections"] == 18, "core catalog compatibility count drift")
    require(stats["combined_structured_sections"] == 27, "combined source count must be 27")
    require(stats["work_volumes_indexed"] == 24, "work-volume index count mismatch")
    require(stats["door_source_profiles"] == 8, "vault door source-profile count mismatch")
    require(stats["stem_source_profiles"] == 10, "vault stem source-profile count mismatch")
    require(casting_reference("YUANLING_QIMEN_CASTING_REFERENCE")["status"] == "SOURCE_REFERENCE_NOT_SEPARATE_PRODUCTION_ENGINE", "casting reference lookup failed")

    require(search_yuanling("截路空亡"), "expanded cutoff-void search failed")
    require(search_yuanling("八門值事"), "expanded door search failed")
    require(search_yuanling("九星克應"), "expanded star-response search failed")
    require(any(row.get("family") == "WORK_TABLE_OF_CONTENTS" for row in search_yuanling("占勝敗")), "work index search failed")

    serialized = json.dumps([extended, work_index, reference], ensure_ascii=False).lower()
    require("數宮3直接等於3球" not in serialized, "forbidden fixed goal rule leaked")
    require("automatic_win_probability" not in serialized, "automatic probability key leaked")

    print(
        "Yuanling expanded DB: PASS | core=18 | extended=9 | combined=27 | "
        "volumes-indexed=24 | doors=8 | stems=10 | numeric-star-context=9+9 | "
        "source-boundaries=preserved"
    )


if __name__ == "__main__":
    main()
