from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

from jsonschema import validate


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from jarvis.yuanling_packet import (  # noqa: E402
    build_yuanling_yanshu_packet,
    verify_yuanling_packet_integrity,
)
from jarvis.yuanling_vault import (  # noqa: E402
    casting_method,
    football_question_templates,
    yuanling_catalog_stats,
)
from qimen.constants import SOLAR_TERM_JU  # noqa: E402
from yuanling.collateral import (  # noqa: E402
    collateral_daily_nine_star_chart,
    collateral_number_palace,
)
from yuanling.riqimen import riqimen_60_day_table  # noqa: E402
from yuanling.stars import star_registry_audit  # noqa: E402
from yuanling.yanshu_qiyao import build_qiyao_review  # noqa: E402


KNOWLEDGE = ROOT / "knowledge"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"Yuanling validation failed: {message}")


def _load(name: str) -> dict:
    return json.loads((KNOWLEDGE / name).read_text(encoding="utf-8"))


def _validate_expanded_catalogs() -> None:
    catalog = _load("yuanling_source_catalog.json")
    casting = _load("casting_method_catalog.json")
    sources = _load("sources.json")

    require(
        catalog.get("schema_version") == "stark-yuanling-source-catalog-v1.0.0",
        "source catalog schema drift",
    )
    sections = catalog.get("sections", [])
    require(len(sections) == 18, "source catalog must contain 18 reviewed sections")
    ids = [row.get("id") for row in sections]
    require(len(ids) == len(set(ids)), "source catalog section ids must be unique")
    require(
        catalog["completion"]["source_locked_riqimen_day_table"] == 60,
        "source catalog Ri-Qimen day coverage drift",
    )
    require(
        catalog["completion"]["numeric_star_daily_judgments"] == 9,
        "value-day numeric-star coverage drift",
    )

    by_id = {row["id"]: row for row in sections}
    qiyao = by_id["yuanling.vol1.qiyao"]
    require(
        qiyao["machine_facts"]["ordered_factors"]
        == ["數宮", "數主", "飛星", "入門", "直日星", "日干", "時支"],
        "expanded source catalog qiyao order mismatch",
    )
    source_ju = by_id["yuanling.vol1.solar_term_ju"]["machine_facts"]
    require(
        {term: tuple(values) for term, values in source_ju.items()} == SOLAR_TERM_JU,
        "Yuanling source solar-term Ju table diverges from production Qimen table",
    )
    value_day = by_id["yuanling.vol3.value_day_nine_stars"]["machine_facts"]
    shefu = by_id["yuanling.vol3.shefu_numeric_associations"]["machine_facts"]
    require(len(value_day) == 9, "value-day nine-star records must cover 1..9")
    require(len(shefu) == 9, "Shefu numeric association records must cover 1..9")
    require(
        [row["number"] for row in value_day] == list(range(1, 10)),
        "value-day nine-star ordering must be 1..9",
    )
    require(
        [row["number"] for row in shefu] == list(range(1, 10)),
        "Shefu numeric association ordering must be 1..9",
    )

    source_ids = {row["id"] for row in sources.get("sources", [])}
    require(
        set(catalog.get("source_ids", [])) <= source_ids,
        "Yuanling source catalog references an unregistered global source id",
    )
    require("yuanling-ctext-vol3" in source_ids, "Yuanling volume-three source missing")

    require(
        casting.get("schema_version") == "stark-casting-method-catalog-v1.0.0",
        "casting method catalog schema drift",
    )
    methods = {row["id"]: row for row in casting.get("methods", [])}
    require(
        set(methods)
        == {
            "QIMEN_SHIJIA_ZHUANPAN_CHAIBU",
            "MEIHUA_YEAR_MONTH_DAY_HOUR",
            "YUANLING_YANSHU_QIYAO_RAW",
            "YUANLING_RI_QIMEN",
        },
        "casting method catalog must contain the four current method contracts",
    )
    require(
        methods["QIMEN_SHIJIA_ZHUANPAN_CHAIBU"]["interpretation_role"]
        == "RESULT_ENGINE_INPUT",
        "Qimen interpretation role drift",
    )
    require(
        methods["MEIHUA_YEAR_MONTH_DAY_HOUR"]["interpretation_role"]
        == "STRUCTURE_STRESS_TEST",
        "Meihua interpretation role drift",
    )
    require(
        methods["YUANLING_RI_QIMEN"]["status"] == "PARTIAL_RESEARCH_ALPHA",
        "Ri-Qimen must remain explicitly partial",
    )
    templates = football_question_templates()
    require(
        "不判比分與進球" in templates["meihua"],
        "Meihua football question must not duplicate Qimen score output",
    )
    require(
        "不直接將宮數或星數換算為比分" in templates["yuanling"],
        "Yuanling football question must preserve score firewall",
    )

    serialized = json.dumps(catalog, ensure_ascii=False).lower()
    require("automatic_win_probability" not in serialized, "source catalog contains auto probability key")
    require("數宮3直接等於3球" not in serialized, "source catalog contains forbidden fixed goal rule")

    stats = yuanling_catalog_stats()
    require(stats["structured_sections"] == 18, "vault stats section count mismatch")
    require(stats["riqimen_day_rows"] == 60, "vault stats Ri-Qimen count mismatch")
    require(casting_method("YUANLING_YANSHU_QIYAO_RAW")["status"] == "RESEARCH_ALPHA", "Qiyao method status drift")


def main() -> None:
    audit = _load("yuanling_method_audit.json")
    collateral_audit = _load("yuanling_collateral_reconstruction.json")
    require(
        audit.get("schema_version") == "stark-yuanling-method-audit-v1.0.0",
        "method audit schema drift",
    )
    require(
        audit.get("project_status") == "SOURCE_AUDIT_READY__ENGINES_SEPARATED",
        "engines must remain separated",
    )
    require(
        audit["source_policy"]["do_not_merge_adjacent_sections_without_explicit_text"]
        is True,
        "section separation rule missing",
    )
    require(
        audit["source_policy"]["do_not_reuse_shijia_star_registry_for_qiyao_by_default"]
        is True,
        "star separation rule missing",
    )
    require(
        audit["source_policy"]["football_score_mapping"] == "DISABLED",
        "football score mapping must remain disabled",
    )
    require(
        set(audit["yanshu_qiyao"]["seven_factors"])
        == {"數宮", "數主", "飛星", "入門", "直日星", "日干", "時支"},
        "seven-factor list mismatch",
    )
    require(
        len(audit["ri_qimen"]["unresolved_algorithmic_points"]) >= 2,
        "Ri-Qimen uncertainty must remain explicit",
    )

    _validate_expanded_catalogs()

    require(
        collateral_audit.get("status")
        == "COLLATERAL_RECONSTRUCTION_AVAILABLE__NOT_PRIMARY_YUANLING_FACT",
        "collateral authority boundary missing",
    )
    require(
        len(collateral_audit.get("collateral_sources", [])) >= 2,
        "collateral source basis incomplete",
    )
    variants = {
        row["id"]: row for row in collateral_audit.get("variant_register", [])
    }
    require(
        variants["QIYAO_FACTOR_4_VARIANT"]["yuanling_primary"] == "四曰入門",
        "factor-four primary wording drift",
    )
    require(
        variants["NUMBER_CHIEF_EXAMPLE_PALACE_VARIANT"]["yuanling_primary"]
        == "假如數在乾宮，黑星為主",
        "black-star primary example drift",
    )

    star_audit = star_registry_audit()
    require(star_audit["count"] == 9, "numeric-star registry must contain nine stars")
    require(
        star_audit["independent_from_shijia_qimen_star_registry"] is True,
        "numeric stars must be independent",
    )
    color_names = {row["color_name"] for row in star_audit["stars"]}
    require(
        "二黑" in color_names and "九紫" in color_names,
        "numeric-star names incomplete",
    )
    require(
        not ({"天蓬", "天芮", "天沖"} & color_names),
        "Shijia stars leaked into numeric-star primary names",
    )

    yang_chart = collateral_daily_nine_star_chart("甲子", "陽遁")
    yin_chart = collateral_daily_nine_star_chart("甲子", "陰遁")
    require(
        yang_chart
        == {
            8: "太乙",
            9: "攝提",
            1: "軒轅",
            2: "招搖",
            3: "天符",
            4: "青龍",
            5: "咸池",
            6: "太陰",
            7: "天乙",
        },
        "collateral yang 甲子 daily-star anchor mismatch",
    )
    require(
        yin_chart
        == {
            2: "太乙",
            1: "攝提",
            9: "軒轅",
            8: "招搖",
            7: "天符",
            6: "青龍",
            5: "咸池",
            4: "太陰",
            3: "天乙",
        },
        "collateral yin 甲子 daily-star anchor mismatch",
    )
    require(
        collateral_number_palace("甲子", "酉", "陽遁") == 5,
        "酉 must repeat 子 in collateral number-palace rule",
    )
    require(
        collateral_number_palace("甲子", "戌", "陽遁") == 6,
        "戌 must repeat 丑 in collateral number-palace rule",
    )

    table = riqimen_60_day_table()
    require(len(table) == 60, "Ri-Qimen day table must cover all 60 days")
    require(
        len({row["day_ganzhi"] for row in table}) == 60,
        "Ri-Qimen day table has duplicates",
    )
    require(
        table[0]["day_ganzhi"] == "甲子"
        and table[0]["rest_door_start_palace"] == 1,
        "甲子 table anchor mismatch",
    )
    require(
        table[-1]["day_ganzhi"] == "癸亥"
        and table[-1]["rest_door_start_palace"] == 4,
        "癸亥 table anchor mismatch",
    )

    event = datetime(2026, 8, 23, 20, 53, tzinfo=ZoneInfo("Asia/Taipei"))
    black_li = build_qiyao_review(
        event,
        "Asia/Taipei",
        number_chief_star_number=2,
        number_chief_landing_palace=9,
    )
    black_zhen = build_qiyao_review(
        event,
        "Asia/Taipei",
        number_chief_star_number=2,
        number_chief_landing_palace=3,
    )
    black_gen = build_qiyao_review(
        event,
        "Asia/Taipei",
        number_chief_star_number=2,
        number_chief_landing_palace=8,
    )
    require(
        black_li["number_chief_landing_state"]["source_song_state"] == "生",
        "二黑到離 should preserve source 生 direction",
    )
    require(
        black_zhen["number_chief_landing_state"]["source_song_state"] == "難",
        "二黑到震 should preserve source 難 direction",
    )
    require(
        black_gen["number_chief_landing_state"]["source_song_state"] == "和",
        "二黑到艮 should preserve source 和 direction",
    )

    packet = build_yuanling_yanshu_packet(
        question="整理《元靈經》演數七要原始資料，不直接輸出足球比分。",
        event_at=event,
        timezone_name="Asia/Taipei",
        mode="QIYAO_RAW",
    )
    schema = json.loads(
        (ROOT / "schemas" / "yuanling_yanshu_packet_v1_2.schema.json").read_text(
            encoding="utf-8"
        )
    )
    validate(packet, schema)
    require(verify_yuanling_packet_integrity(packet), "packet SHA integrity failed")
    require(
        packet["schema_version"] == "YUANLING_YANSHU_PACKET_V1_2",
        "packet version must be v1.2",
    )
    require(
        packet["riqimen_base"] is None,
        "QIYAO_RAW must not silently inject Ri-Qimen",
    )
    require(
        packet["qiyao_review"]["riqimen_bridge"]["status"] == "NOT_REQUESTED",
        "raw mode Ri-Qimen bridge status mismatch",
    )
    require(
        "riqimen_experiment_input" not in packet["qiyao_review"],
        "Qiyao review must not duplicate Ri-Qimen payload",
    )
    reconstruction = packet["qiyao_review"]["collateral_reconstruction"]
    require(
        reconstruction["status"] == "CANDIDATES_ONLY__NOT_PRIMARY_YUANLING_FACTS",
        "collateral candidates were promoted",
    )
    factors = {row["name"]: row for row in packet["qiyao_review"]["seven_factors"]}
    require(factors["數宮"]["value"] is None, "collateral 數宮 must not fill primary slot")
    require(factors["飛星"]["value"] is None, "collateral 飛星 must not fill primary slot")
    require(
        packet["qiyao_review"]["raw_numeric_candidates"]["values"] == [],
        "numeric candidates must stay disabled",
    )
    require(
        packet["knowledge_context"]["method"]["id"] == "YUANLING_YANSHU_QIYAO_RAW",
        "knowledge context method mismatch",
    )
    context_ids = {row["id"] for row in packet["knowledge_context"]["source_sections"]}
    require(
        {"yuanling.vol1.qiyao", "yuanling.vol1.number_chief_song", "yuanling.vol3.value_day_nine_stars"}
        <= context_ids,
        "packet source context incomplete",
    )
    require(
        "AUTOMATIC_FOOTBALL_SCORE_FROM_PALACE_NUMBER" in packet["forbidden_outputs"],
        "score shortcut guard missing",
    )
    require(
        "COLLATERAL_CANDIDATE_PROMOTED_TO_PRIMARY_FACT" in packet["forbidden_outputs"],
        "collateral promotion guard missing",
    )
    require(
        "SHEFU_NUMBER_ASSOCIATION_TO_FOOTBALL_GOALS" in packet["forbidden_outputs"],
        "Shefu-to-goals guard missing",
    )

    experiment = build_yuanling_yanshu_packet(
        question="以實驗串接保存日奇門 base 與演數七要，兩者不得混成古法定論。",
        event_at=event,
        timezone_name="Asia/Taipei",
        mode="RIQIMEN_QIYAO_EXPERIMENT",
    )
    validate(experiment, schema)
    require(verify_yuanling_packet_integrity(experiment), "experiment packet SHA integrity failed")
    require(
        experiment["riqimen_base"] is not None,
        "experiment mode must expose Ri-Qimen independently",
    )
    require(
        experiment["riqimen_base"]["status"].startswith("PARTIAL_SOURCE_GROUNDED"),
        "Ri-Qimen status must remain honest",
    )
    require(
        experiment["qiyao_review"]["riqimen_bridge"]["status"]
        == "PACKET_LAYER_SIBLING_ENABLED",
        "experiment bridge must point to packet-layer sibling",
    )
    require(
        "riqimen_experiment_input" not in experiment["qiyao_review"],
        "experiment must not duplicate Ri-Qimen inside Qiyao review",
    )
    require(
        experiment["knowledge_context"]["riqimen_method"]["id"] == "YUANLING_RI_QIMEN",
        "experiment knowledge context must expose Ri-Qimen method",
    )

    print(
        "Yuanling: PASS | packet=v1.2 | source_sections=18 | casting_methods=4 | "
        "sections=separate | numeric_stars=9 | riqimen=sibling-only | "
        "collateral=candidates-only | riqimen_day_table=60 | score_mapping=disabled | "
        "source-context=embedded | unresolved_rules=preserved"
    )


if __name__ == "__main__":
    main()
