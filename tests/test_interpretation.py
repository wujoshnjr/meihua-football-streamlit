from __future__ import annotations

from datetime import timedelta

from qimen.engine import cast_qimen
from qimen.interpretation import (
    all_relation_readings,
    build_interpretation_guide,
    build_relation,
    interpretation_stats,
    search_relation_readings,
)
from qimen.protocol import MatchInput


def test_relation_matrix_is_total_and_matches_contract():
    stats = interpretation_stats()
    assert stats["total_relations"] == 306
    assert stats["relation_counts"] == {
        "stem_pair": 81,
        "star_door": 72,
        "door_palace": 72,
        "star_palace": 81,
    }
    assert len({item.key for item in all_relation_readings()}) == 306


def test_named_classics_are_separated_from_composed_relations():
    named = build_relation("stem_pair", "戊", "丙")
    assert named.classical_pattern == "青龍返首"
    assert named.authority == "古籍固定格名"
    assert named.source_id == "qimen-daquan-ten-stems"

    composed = build_relation("stem_pair", "戊", "乙")
    assert composed.classical_pattern is None
    assert "五行組合推導" in composed.authority
    assert "不是杜撰" in composed.caution


def test_door_palace_pressure_direction_is_explicit():
    door_pressure = build_relation("door_palace", "傷門", 2)
    assert door_pressure.classical_pattern == "門迫"
    assert door_pressure.element_relation == "前剋後"

    palace_pressure = build_relation("door_palace", "休門", 2)
    assert palace_pressure.classical_pattern == "宮迫"
    assert palace_pressure.element_relation == "後剋前"


def test_relation_search_crosses_all_four_matrices():
    assert search_relation_readings("青龍返首")[0].classical_pattern == "青龍返首"
    tian_chong = search_relation_readings("天沖")
    assert {item.relation_type for item in tian_chong} == {"star_door", "star_palace"}
    assert len(search_relation_readings(relation_type="star_door")) == 72


def test_board_guide_locks_question_focus_roles_and_relations(calendar_context):
    match = MatchInput(
        "GUIDE-TEST",
        "Home",
        "Away",
        "League",
        calendar_context.local_datetime,
        calendar_context.timezone_name,
        "Stadium",
        "Taipei",
    )
    board = cast_qimen(match.event_at, match.timezone_name, calendar=calendar_context)
    guide = build_interpretation_guide(
        board,
        question="雙方的逼搶與攻守轉換最可能如何展開？",
        focus_id="pressing_transition",
        match=match,
        locked_at=calendar_context.local_datetime - timedelta(hours=8),
    )
    assert guide.focus_name == "逼搶與攻守轉換"
    assert guide.home_use_god.role == "主隊／日干"
    assert guide.away_use_god.role == "客隊／時干"
    assert guide.audit.overall == "WARN"  # no external prematch evidence
    assert len(guide.audit.checks) == 10
    assert len(guide.reading_order) == 10
    assert len(guide.palace_guides) == 9
    assert any(palace.relations for palace in guide.palace_guides)
    assert "不宣稱窮盡" in guide.boundary
    lock_check = next(item for item in guide.audit.checks if item.id == "lock_timestamp")
    assert lock_check.status == "PASS"


def test_historical_guide_is_not_mislabelled_as_prematch(calendar_context):
    match = MatchInput(
        "HISTORICAL",
        "Home",
        "Away",
        "League",
        calendar_context.local_datetime,
        calendar_context.timezone_name,
        "Stadium",
        "Taipei",
    )
    board = cast_qimen(match.event_at, match.timezone_name, calendar=calendar_context)
    guide = build_interpretation_guide(
        board,
        question="本場雙方最可能呈現哪些可觀察的攻守結構？",
        match=match,
        locked_at=calendar_context.local_datetime + timedelta(hours=1),
        locked_before_cast=True,
    )
    lock_check = next(item for item in guide.audit.checks if item.id == "lock_timestamp")
    assert lock_check.status == "WARN"
    assert "回溯" in lock_check.detail
