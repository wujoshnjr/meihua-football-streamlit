from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from jsonschema import validate

from jarvis.yuanling_packet import (
    build_yuanling_yanshu_packet,
    verify_yuanling_packet_integrity,
)
from jarvis.yuanling_vault import (
    casting_method,
    football_question_templates,
    search_yuanling,
    yuanling_catalog_stats,
)
from yuanling.collateral import (
    collateral_daily_nine_star_chart,
    collateral_number_palace,
    collateral_qiyao_star_roles,
)
from yuanling.riqimen import (
    build_riqimen_base,
    chuangong_star_plate,
    rest_door_start_palace,
    riqimen_60_day_table,
    riqimen_door_plate,
)
from yuanling.stars import numeric_star, numeric_star_by_alias, star_registry_audit
from yuanling.yanshu_qiyao import build_qiyao_review


ROOT = Path(__file__).resolve().parents[1]


def _event() -> datetime:
    return datetime(2026, 8, 23, 20, 53, tzinfo=ZoneInfo("Asia/Taipei"))


def test_riqimen_60_day_rest_door_table_is_exact_and_complete() -> None:
    rows = riqimen_60_day_table()
    assert len(rows) == 60
    assert len({row["day_ganzhi"] for row in rows}) == 60
    assert rows[0]["day_index"] == 1
    assert rows[-1]["day_index"] == 60
    assert [row["rest_door_start_palace"] for row in rows[:24:3]] == [
        1,
        2,
        3,
        4,
        6,
        7,
        8,
        9,
    ]
    assert rest_door_start_palace("甲子") == 1
    assert rest_door_start_palace("乙酉") == 9
    assert rest_door_start_palace("癸亥") == 4


def test_riqimen_chuangong_is_numeric_forward_and_crosses_center() -> None:
    # 《奇門遁甲統宗》日奇門：甲子天蓬起艮八、芮在離九，順飛九宮。
    assert chuangong_star_plate(1, 8) == {
        8: "天蓬",
        9: "天芮",
        1: "天沖",
        2: "天輔",
        3: "天禽",
        4: "天心",
        5: "天柱",
        6: "天任",
        7: "天英",
    }
    plate = chuangong_star_plate(7, 5)
    assert len(plate) == 9
    assert 5 in plate
    assert set(plate) == set(range(1, 10))
    assert len(set(plate.values())) == 9


def test_riqimen_door_plate_uses_primary_rest_anchor_and_skips_center() -> None:
    assert riqimen_door_plate("甲子") == {
        1: "休門",
        8: "生門",
        3: "傷門",
        4: "杜門",
        9: "景門",
        2: "死門",
        7: "驚門",
        6: "開門",
    }
    dingmao = riqimen_door_plate("丁卯")
    assert dingmao[2] == "休門"
    assert len(dingmao) == 8
    assert 5 not in dingmao


def test_numeric_star_registry_is_independent_from_shijia_names() -> None:
    audit = star_registry_audit()
    assert audit["count"] == 9
    assert audit["independent_from_shijia_qimen_star_registry"] is True
    assert numeric_star(2).color_name == "二黑"
    assert numeric_star_by_alias("巨門").number == 2
    assert numeric_star_by_alias("攝提").number == 2
    assert not {"天蓬", "天芮", "天沖"} & {
        star["color_name"] for star in audit["stars"]
    }


def test_collateral_day_nine_star_jiazi_anchors_are_exact() -> None:
    assert collateral_daily_nine_star_chart("甲子", "陽遁") == {
        8: "太乙",
        9: "攝提",
        1: "軒轅",
        2: "招搖",
        3: "天符",
        4: "青龍",
        5: "咸池",
        6: "太陰",
        7: "天乙",
    }
    assert collateral_daily_nine_star_chart("甲子", "陰遁") == {
        2: "太乙",
        1: "攝提",
        9: "軒轅",
        8: "招搖",
        7: "天符",
        6: "青龍",
        5: "咸池",
        4: "太陰",
        3: "天乙",
    }


def test_collateral_number_palace_preserves_dongting_hour_rule() -> None:
    assert collateral_number_palace("甲子", "子", "陽遁") == 5
    assert collateral_number_palace("甲子", "丑", "陽遁") == 6
    assert collateral_number_palace("甲子", "酉", "陽遁") == 5
    assert collateral_number_palace("甲子", "戌", "陽遁") == 6
    assert collateral_number_palace("乙丑", "子", "陽遁") == 6
    assert collateral_number_palace("乙丑", "子", "陰遁") == 4


def test_number_chief_flying_star_and_value_day_star_are_distinct_roles() -> None:
    roles = collateral_qiyao_star_roles("甲子", "甲午", "陽遁")
    assert roles["number_palace"] == 2

    # 數主: 數宮坤二 -> 二黑/攝提；追蹤它飛到哪一宮（甲子陽遁在離九）。
    assert roles["number_chief"]["star_number"] == 2
    assert roles["number_chief"]["color_name"] == "二黑"
    assert roles["number_chief"]["landing_palace"] == 9

    # 飛星: 反向查「目前誰臨數宮」；甲子陽遁坤二上是招搖/四綠。
    assert roles["flying_star"]["star_number"] == 4
    assert roles["flying_star"]["daily_alias"] == "招搖"

    # 直日星: 獨立看中五；甲子陽遁中五是咸池/七赤。
    assert roles["value_day_star"]["star_number"] == 7
    assert roles["value_day_star"]["daily_alias"] == "咸池"

    assert roles["relation"]["number_chief_is_not_flying_star_by_definition"] is True
    assert roles["relation"]["value_day_is_not_number_chief_by_definition"] is True
    assert "乾宮" in roles["textual_variant_warning"]["yuanling_transmitted_example"]
    assert "坤宮" in roles["textual_variant_warning"]["qimen_baojian_parallel_example"]


def test_black_star_source_example_direction_is_preserved() -> None:
    li = build_qiyao_review(
        _event(),
        "Asia/Taipei",
        number_chief_star_number=2,
        number_chief_landing_palace=9,
    )
    zhen = build_qiyao_review(
        _event(),
        "Asia/Taipei",
        number_chief_star_number=2,
        number_chief_landing_palace=3,
    )
    gen = build_qiyao_review(
        _event(),
        "Asia/Taipei",
        number_chief_star_number=2,
        number_chief_landing_palace=8,
    )
    assert li["number_chief_landing_state"]["source_song_state"] == "生"
    assert zhen["number_chief_landing_state"]["source_song_state"] == "難"
    assert gen["number_chief_landing_state"]["source_song_state"] == "和"


def test_crosschecked_roles_do_not_silently_fill_primary_qiyao_factors() -> None:
    review = build_qiyao_review(_event(), "Asia/Taipei", mode="QIYAO_RAW")
    factors = {row["name"]: row for row in review["seven_factors"]}
    collateral = review["collateral_reconstruction"]

    assert collateral["status"] == "CANDIDATES_ONLY__NOT_PRIMARY_YUANLING_FACTS"
    assert collateral["number_palace_candidate"]["palace"] in range(1, 10)
    assert collateral["number_palace_candidate"]["adopt_as_primary_factor"] is False
    assert review["star_role_resolution"]["status"] == (
        "ROLE_RELATIONSHIP_RESOLVED__IDENTITY_MAPPING_CROSSCHECKED"
    )
    assert review["star_role_resolution"]["primary_slots_auto_filled"] is False
    assert factors["數宮"]["value"] is None
    assert factors["數主"]["value"] is None
    assert factors["飛星"]["value"] is None
    assert factors["直日星"]["value"] is None
    assert review["raw_numeric_candidates"]["values"] == []


def test_qiyao_review_never_embeds_riqimen_payload() -> None:
    raw = build_qiyao_review(_event(), "Asia/Taipei", mode="QIYAO_RAW")
    experiment = build_qiyao_review(
        _event(),
        "Asia/Taipei",
        mode="RIQIMEN_QIYAO_EXPERIMENT",
    )

    assert "riqimen_experiment_input" not in raw
    assert "riqimen_experiment_input" not in experiment
    assert raw["riqimen_bridge"]["status"] == "NOT_REQUESTED"
    assert experiment["riqimen_bridge"]["status"] == "PACKET_LAYER_SIBLING_ENABLED"
    assert raw["raw_numeric_candidates"]["values"] == []
    assert experiment["raw_numeric_candidates"]["values"] == []


def test_yuanling_source_catalog_and_casting_catalog_are_searchable() -> None:
    stats = yuanling_catalog_stats()
    # This catalog intentionally grows as more Yuanling material is materialized.
    assert stats["structured_sections"] >= 18
    assert stats["numeric_stars"] == 9
    assert stats["riqimen_day_rows"] == 60
    assert stats["yuanling_methods"] == 3
    assert stats["source_schema"] == "stark-yuanling-source-catalog-v1.0.0"
    assert stats["casting_schema"] == "stark-casting-method-catalog-v1.1.0"

    qiyao_hits = search_yuanling("演數七要")
    assert any(row.get("key") == "yuanling.vol1.qiyao" for row in qiyao_hits)
    riqimen_hits = search_yuanling("甲子")
    assert any(row.get("family") == "RIQIMEN_60_DAY_REST_DOOR_TABLE" for row in riqimen_hits)
    casting_hits = search_yuanling("年月日時起卦")
    assert any(row.get("key") == "MEIHUA_YEAR_MONTH_DAY_HOUR" for row in casting_hits)


def test_casting_method_catalog_keeps_system_roles_and_question_templates() -> None:
    qimen = casting_method("QIMEN_SHIJIA_ZHUANPAN_CHAIBU")
    meihua = casting_method("MEIHUA_YEAR_MONTH_DAY_HOUR")
    qiyao = casting_method("YUANLING_YANSHU_QIYAO_RAW")
    riqimen = casting_method("YUANLING_RI_QIMEN")
    templates = football_question_templates()

    assert qimen["interpretation_role"] == "RESULT_ENGINE_INPUT"
    assert meihua["interpretation_role"] == "STRUCTURE_STRESS_TEST"
    assert qiyao["interpretation_role"] == "NUMERIC_DIVINATION_RESEARCH_INPUT"
    assert riqimen["status"] == "SOURCE_CROSSCHECKED_RECONSTRUCTION_ALPHA"
    assert "不判比分與進球" in templates["meihua"]
    assert "不直接將宮數或星數換算為比分" in templates["yuanling"]


def test_riqimen_build_exposes_resolved_chuangong_without_reusing_shijia_ring() -> None:
    board = build_riqimen_base(_event(), "Asia/Taipei")
    assert board["kind"] == "YUANLING_RI_QIMEN_BASE_V2"
    assert board["status"] == "SOURCE_CROSSCHECKED_RECONSTRUCTION_READY"
    assert board["algorithm_resolution"]["chuangong"]["status"] == (
        "RESOLVED_BY_PRIMARY_TEXT_PLUS_DAY_QIMEN_CROSSCHECK"
    )
    assert board["algorithm_resolution"]["chuangong"]["uses_production_rotating_ring"] is False
    assert len(board["source_reconstructed"]["chuangong_star_plate"]) == 9
    assert 5 in board["source_reconstructed"]["chuangong_star_plate"]
    assert len(board["source_reconstructed"]["door_plate"]) == 8
    assert 5 not in board["source_reconstructed"]["door_plate"]


def test_yuanling_packet_is_deterministic_integrity_checked_and_schema_valid() -> None:
    kwargs = dict(
        question="依《元靈經》演數七要整理此事件之數術原始資料，不直接轉成足球比分。",
        event_at=_event(),
        timezone_name="Asia/Taipei",
        mode="QIYAO_RAW",
    )
    first = build_yuanling_yanshu_packet(**kwargs)
    second = build_yuanling_yanshu_packet(**kwargs)
    assert first == second
    assert verify_yuanling_packet_integrity(first)
    assert first["schema_version"] == "YUANLING_YANSHU_PACKET_V1_3"
    assert first["mode"] == "QIYAO_RAW"
    assert first["riqimen_base"] is None
    assert first["qiyao_review"]["riqimen_bridge"]["status"] == "NOT_REQUESTED"
    assert first["knowledge_context"]["method"]["id"] == "YUANLING_YANSHU_QIYAO_RAW"
    assert first["knowledge_context"]["riqimen_method"] is None
    source_ids = {row["id"] for row in first["knowledge_context"]["source_sections"]}
    assert "yuanling.vol1.qiyao" in source_ids
    assert "yuanling.vol1.number_chief_song" in source_ids
    assert "yuanling.vol3.value_day_nine_stars" in source_ids
    assert "yuanling.vol3.shefu_numeric_associations" in source_ids
    assert (
        first["ai_interpretation_contract"]["score_synthesis"]
        == "DEFERRED_UNTIL_BLIND_TEST_PROTOCOL"
    )
    assert "AUTOMATIC_FOOTBALL_SCORE_FROM_PALACE_NUMBER" in first["forbidden_outputs"]
    assert "COLLATERAL_CANDIDATE_PROMOTED_TO_PRIMARY_FACT" in first["forbidden_outputs"]
    assert "SHEFU_NUMBER_ASSOCIATION_TO_FOOTBALL_GOALS" in first["forbidden_outputs"]
    assert "TEXTUAL_VARIANT_SILENTLY_NORMALIZED" in first["forbidden_outputs"]

    schema = json.loads(
        (ROOT / "schemas" / "yuanling_yanshu_packet_v1_3.schema.json").read_text(
            encoding="utf-8"
        )
    )
    validate(first, schema)


def test_riqimen_experiment_uses_single_packet_layer_sibling() -> None:
    packet = build_yuanling_yanshu_packet(
        question="並列保存七要與日奇門，但不混成單一古法。",
        event_at=_event(),
        timezone_name="Asia/Taipei",
        mode="RIQIMEN_QIYAO_EXPERIMENT",
    )
    schema = json.loads(
        (ROOT / "schemas" / "yuanling_yanshu_packet_v1_3.schema.json").read_text(
            encoding="utf-8"
        )
    )

    validate(packet, schema)
    assert verify_yuanling_packet_integrity(packet)
    assert packet["riqimen_base"]["kind"] == "YUANLING_RI_QIMEN_BASE_V2"
    assert packet["riqimen_base"]["algorithm_resolution"]["chuangong"]["status"] == (
        "RESOLVED_BY_PRIMARY_TEXT_PLUS_DAY_QIMEN_CROSSCHECK"
    )
    assert packet["qiyao_review"]["riqimen_bridge"]["status"] == (
        "PACKET_LAYER_SIBLING_ENABLED"
    )
    assert "riqimen_experiment_input" not in packet["qiyao_review"]
    assert packet["knowledge_context"]["riqimen_method"]["id"] == "YUANLING_RI_QIMEN"
    source_ids = {row["id"] for row in packet["knowledge_context"]["source_sections"]}
    assert "yuanling.vol1.riqimen" in source_ids
    assert "yuanling.vol1.solar_term_ju" in source_ids
