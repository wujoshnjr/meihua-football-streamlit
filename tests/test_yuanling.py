from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from jsonschema import validate

from jarvis.yuanling_packet import build_yuanling_yanshu_packet, verify_yuanling_packet_integrity
from yuanling.riqimen import rest_door_start_palace, riqimen_60_day_table
from yuanling.stars import numeric_star, numeric_star_by_alias, star_registry_audit
from yuanling.yanshu_qiyao import build_qiyao_review


ROOT = Path(__file__).resolve().parents[1]


def _event() -> datetime:
    return datetime(2026, 8, 23, 20, 53, tzinfo=ZoneInfo("Asia/Taipei"))


def test_riqimen_60_day_rest_door_table_is_exact_and_complete() -> None:
    rows = riqimen_60_day_table()
    assert len(rows) == 60
    assert len({row["day_ganzhi"] for row in rows}) == 60
    assert [row["rest_door_start_palace"] for row in rows[:24:3]] == [1, 2, 3, 4, 6, 7, 8, 9]
    assert rest_door_start_palace("甲子") == 1
    assert rest_door_start_palace("乙酉") == 9
    assert rest_door_start_palace("癸亥") == 4


def test_numeric_star_registry_is_independent_from_shijia_names() -> None:
    audit = star_registry_audit()
    assert audit["count"] == 9
    assert audit["independent_from_shijia_qimen_star_registry"] is True
    assert numeric_star(2).color_name == "二黑"
    assert numeric_star_by_alias("巨門").number == 2
    assert numeric_star_by_alias("攝提").number == 2
    assert not {"天蓬", "天芮", "天沖"} & {star["color_name"] for star in audit["stars"]}


def test_black_star_source_example_direction_is_preserved() -> None:
    li = build_qiyao_review(
        _event(), "Asia/Taipei", number_chief_star_number=2, number_chief_landing_palace=9
    )
    zhen = build_qiyao_review(
        _event(), "Asia/Taipei", number_chief_star_number=2, number_chief_landing_palace=3
    )
    gen = build_qiyao_review(
        _event(), "Asia/Taipei", number_chief_star_number=2, number_chief_landing_palace=8
    )
    assert li["number_chief_landing_state"]["source_song_state"] == "生"
    assert zhen["number_chief_landing_state"]["source_song_state"] == "難"
    assert gen["number_chief_landing_state"]["source_song_state"] == "和"


def test_qiyao_raw_and_riqimen_experiment_remain_separate() -> None:
    raw = build_qiyao_review(_event(), "Asia/Taipei", mode="QIYAO_RAW")
    experiment = build_qiyao_review(_event(), "Asia/Taipei", mode="RIQIMEN_QIYAO_EXPERIMENT")
    assert raw["riqimen_experiment_input"] is None
    assert experiment["riqimen_experiment_input"]["kind"] == "YUANLING_RI_QIMEN_BASE_V1"
    assert experiment["riqimen_experiment_input"]["status"].startswith("PARTIAL_SOURCE_GROUNDED")
    assert raw["raw_numeric_candidates"]["values"] == []
    assert experiment["raw_numeric_candidates"]["values"] == []


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
    assert first["mode"] == "QIYAO_RAW"
    assert first["riqimen_base"] is None
    assert first["ai_interpretation_contract"]["score_synthesis"] == "DEFERRED_UNTIL_BLIND_TEST_PROTOCOL"
    assert "AUTOMATIC_FOOTBALL_SCORE_FROM_PALACE_NUMBER" in first["forbidden_outputs"]

    schema = json.loads(
        (ROOT / "schemas" / "yuanling_yanshu_packet_v1.schema.json").read_text(encoding="utf-8")
    )
    validate(first, schema)
