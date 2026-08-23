from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

from jsonschema import validate


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from jarvis.yuanling_packet import build_yuanling_yanshu_packet  # noqa: E402
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


def main() -> None:
    audit = json.loads(
        (KNOWLEDGE / "yuanling_method_audit.json").read_text(encoding="utf-8")
    )
    collateral_audit = json.loads(
        (KNOWLEDGE / "yuanling_collateral_reconstruction.json").read_text(
            encoding="utf-8"
        )
    )
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
        (ROOT / "schemas" / "yuanling_yanshu_packet_v1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    validate(packet, schema)
    require(
        packet["riqimen_base"] is None,
        "QIYAO_RAW must not silently inject Ri-Qimen",
    )
    reconstruction = packet["qiyao_review"]["collateral_reconstruction"]
    require(
        reconstruction["status"] == "CANDIDATES_ONLY__NOT_PRIMARY_YUANLING_FACTS",
        "collateral candidates were promoted",
    )
    factors = {row["name"]: row for row in packet["qiyao_review"]["seven_factors"]}
    require(factors["數宮"]["value"] is None, "collateral 数宫 must not fill primary slot")
    require(factors["飛星"]["value"] is None, "collateral 飞星 must not fill primary slot")
    require(
        packet["qiyao_review"]["raw_numeric_candidates"]["values"] == [],
        "numeric candidates must stay disabled",
    )
    require(
        "AUTOMATIC_FOOTBALL_SCORE_FROM_PALACE_NUMBER" in packet["forbidden_outputs"],
        "score shortcut guard missing",
    )

    experiment = build_yuanling_yanshu_packet(
        question="以實驗串接保存日奇門 base 與演數七要，兩者不得混成古法定論。",
        event_at=event,
        timezone_name="Asia/Taipei",
        mode="RIQIMEN_QIYAO_EXPERIMENT",
    )
    require(
        experiment["riqimen_base"] is not None,
        "experiment mode must expose Ri-Qimen independently",
    )
    require(
        experiment["riqimen_base"]["status"].startswith("PARTIAL_SOURCE_GROUNDED"),
        "Ri-Qimen status must remain honest",
    )

    print(
        "Yuanling: PASS | sections=separate | numeric_stars=9 | "
        "collateral-reconstruction=candidates-only | riqimen_day_table=60 | "
        "score_mapping=disabled | unresolved_rules=preserved"
    )


if __name__ == "__main__":
    main()
