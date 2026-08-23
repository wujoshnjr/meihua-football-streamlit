from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from jsonschema import validate

from jarvis.yuanling_packet import build_yuanling_yanshu_packet
from yuanling.riqimen import riqimen_60_day_table
from yuanling.stars import star_registry_audit
from yuanling.yanshu_qiyao import build_qiyao_review


ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE = ROOT / "knowledge"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"Yuanling validation failed: {message}")


def main() -> None:
    audit = json.loads((KNOWLEDGE / "yuanling_method_audit.json").read_text(encoding="utf-8"))
    require(audit.get("schema_version") == "stark-yuanling-method-audit-v1.0.0", "method audit schema drift")
    require(audit.get("project_status") == "SOURCE_AUDIT_READY__ENGINES_SEPARATED", "engines must remain separated")
    require(audit["source_policy"]["do_not_merge_adjacent_sections_without_explicit_text"] is True, "section separation rule missing")
    require(audit["source_policy"]["do_not_reuse_shijia_star_registry_for_qiyao_by_default"] is True, "star separation rule missing")
    require(audit["source_policy"]["football_score_mapping"] == "DISABLED", "football score mapping must remain disabled")
    require(set(audit["yanshu_qiyao"]["seven_factors"]) == {"數宮", "數主", "飛星", "入門", "直日星", "日干", "時支"}, "seven-factor list mismatch")
    require(len(audit["ri_qimen"]["unresolved_algorithmic_points"]) >= 2, "Ri-Qimen uncertainty must remain explicit")

    star_audit = star_registry_audit()
    require(star_audit["count"] == 9, "numeric-star registry must contain nine stars")
    require(star_audit["independent_from_shijia_qimen_star_registry"] is True, "numeric stars must be independent")
    color_names = {row["color_name"] for row in star_audit["stars"]}
    require("二黑" in color_names and "九紫" in color_names, "numeric-star names incomplete")
    require(not ({"天蓬", "天芮", "天沖"} & color_names), "Shijia stars leaked into numeric-star primary names")

    table = riqimen_60_day_table()
    require(len(table) == 60, "Ri-Qimen day table must cover all 60 days")
    require(len({row["day_ganzhi"] for row in table}) == 60, "Ri-Qimen day table has duplicates")
    require(table[0]["day_ganzhi"] == "甲子" and table[0]["rest_door_start_palace"] == 1, "甲子 table anchor mismatch")
    require(table[-1]["day_ganzhi"] == "癸亥" and table[-1]["rest_door_start_palace"] == 4, "癸亥 table anchor mismatch")

    event = datetime(2026, 8, 23, 20, 53, tzinfo=ZoneInfo("Asia/Taipei"))
    black_li = build_qiyao_review(event, "Asia/Taipei", number_chief_star_number=2, number_chief_landing_palace=9)
    black_zhen = build_qiyao_review(event, "Asia/Taipei", number_chief_star_number=2, number_chief_landing_palace=3)
    black_gen = build_qiyao_review(event, "Asia/Taipei", number_chief_star_number=2, number_chief_landing_palace=8)
    require(black_li["number_chief_landing_state"]["source_song_state"] == "生", "二黑到離 should preserve source 生 direction")
    require(black_zhen["number_chief_landing_state"]["source_song_state"] == "難", "二黑到震 should preserve source 難 direction")
    require(black_gen["number_chief_landing_state"]["source_song_state"] == "和", "二黑到艮 should preserve source 和 direction")

    packet = build_yuanling_yanshu_packet(
        question="整理《元靈經》演數七要原始資料，不直接輸出足球比分。",
        event_at=event,
        timezone_name="Asia/Taipei",
        mode="QIYAO_RAW",
    )
    schema = json.loads((ROOT / "schemas" / "yuanling_yanshu_packet_v1.schema.json").read_text(encoding="utf-8"))
    validate(packet, schema)
    require(packet["riqimen_base"] is None, "QIYAO_RAW must not silently inject Ri-Qimen")
    require(packet["qiyao_review"]["raw_numeric_candidates"]["values"] == [], "numeric candidates must stay disabled")
    require("AUTOMATIC_FOOTBALL_SCORE_FROM_PALACE_NUMBER" in packet["forbidden_outputs"], "score shortcut guard missing")

    experiment = build_yuanling_yanshu_packet(
        question="以實驗串接保存日奇門 base 與演數七要，兩者不得混成古法定論。",
        event_at=event,
        timezone_name="Asia/Taipei",
        mode="RIQIMEN_QIYAO_EXPERIMENT",
    )
    require(experiment["riqimen_base"] is not None, "experiment mode must expose Ri-Qimen independently")
    require(experiment["riqimen_base"]["status"].startswith("PARTIAL_SOURCE_GROUNDED"), "Ri-Qimen status must remain honest")

    print(
        "Yuanling: PASS | sections=separate | numeric_stars=9 | "
        "riqimen_day_table=60 | score_mapping=disabled | unresolved_rules=preserved"
    )


if __name__ == "__main__":
    main()
