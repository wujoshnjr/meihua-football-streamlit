from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import json
from jsonschema import Draft202012Validator, FormatChecker

from jarvis.liuyao_packet import build_liuyao_packet, verify_liuyao_packet_integrity
from liuyao.constants import BAGONG_SEQUENCE, HEXAGRAM_NAME_BY_TRIGRAMS, HEXAGRAM_PALACE, NAJIA
from liuyao.engine import cast_liuyao
from liuyao.review import build_liuyao_review, question_role


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "schemas" / "liuyao_packet_v1.schema.json").read_text(encoding="utf-8"))
VALIDATOR = Draft202012Validator(SCHEMA, format_checker=FormatChecker())


def _event() -> datetime:
    return datetime(2026, 8, 27, 20, 0, tzinfo=ZoneInfo("Asia/Taipei"))


def test_liuyao_tables_cover_all_64_hexagrams_once() -> None:
    names = [name for rows in BAGONG_SEQUENCE.values() for name in rows]
    assert len(names) == 64
    assert len(set(names)) == 64
    assert set(names) == set(HEXAGRAM_NAME_BY_TRIGRAMS.values())
    assert set(names) == set(HEXAGRAM_PALACE)
    assert set(NAJIA) == {"乾", "兌", "離", "震", "巽", "坎", "艮", "坤"}


def test_qian_pure_hexagram_najia_relatives_and_shi_ying() -> None:
    chart = cast_liuyao([7, 7, 7, 7, 7, 7], _event(), "Asia/Taipei")

    assert chart.original_hexagram == "乾為天"
    assert chart.changed_hexagram == "乾為天"
    assert chart.palace == "乾"
    assert chart.palace_stage == "本宮六世"
    assert chart.shi_line == 6
    assert chart.ying_line == 3
    assert chart.moving_lines == ()
    assert [line.branch for line in chart.lines] == ["子", "寅", "辰", "午", "申", "戌"]
    assert [line.stem for line in chart.lines] == ["甲", "甲", "甲", "壬", "壬", "壬"]
    assert [line.relative for line in chart.lines] == ["子孫", "妻財", "父母", "官鬼", "兄弟", "父母"]
    assert chart.original_is_six_clash is True


def test_tianfeng_gou_is_qian_palace_first_generation() -> None:
    chart = cast_liuyao([8, 7, 7, 7, 7, 7], _event(), "Asia/Taipei")

    assert chart.original_hexagram == "天風姤"
    assert chart.palace == "乾"
    assert chart.palace_stage == "一世"
    assert chart.shi_line == 1
    assert chart.ying_line == 4
    assert [line.branch for line in chart.lines] == ["丑", "亥", "酉", "午", "申", "戌"]


def test_zengshan_buyi_xu_to_song_golden_transformed_relatives() -> None:
    # 《增刪卜易》動變章列「水天需變天水訟」；
    # 變爻六親仍依正卦坤宮（土）推，而不是依變卦自身卦宮重算。
    chart = cast_liuyao([9, 7, 9, 6, 7, 6], _event(), "Asia/Taipei")

    assert chart.original_hexagram == "水天需"
    assert chart.changed_hexagram == "天水訟"
    assert chart.palace == "坤"
    assert chart.palace_element == "土"
    assert chart.moving_lines == (1, 3, 4, 6)

    by_pos = {line.position: line for line in chart.lines}
    assert (by_pos[1].relative, by_pos[1].changed_branch, by_pos[1].changed_relative) == ("妻財", "寅", "官鬼")
    assert (by_pos[3].relative, by_pos[3].changed_branch, by_pos[3].changed_relative) == ("兄弟", "午", "父母")
    assert (by_pos[4].relative, by_pos[4].changed_branch, by_pos[4].changed_relative) == ("子孫", "午", "父母")
    assert (by_pos[6].relative, by_pos[6].changed_branch, by_pos[6].changed_relative) == ("妻財", "戌", "兄弟")


def test_use_god_review_does_not_hide_multiple_or_unmapped_candidates() -> None:
    qian = cast_liuyao([7, 7, 7, 7, 7, 7], _event(), "Asia/Taipei")
    wealth = build_liuyao_review(qian, question_category="WEALTH")
    assert wealth.use_god_review["status"] == "SINGLE_CANDIDATE_READY"
    candidate = wealth.use_god_review["candidates"][0]
    assert candidate["position"] == 2
    assert candidate["relative"] == "妻財"
    assert candidate["spirit_roles"]["元神五行"] == "水"
    assert candidate["spirit_roles"]["忌神五行"] == "金"
    assert candidate["spirit_roles"]["仇神五行"] == "土"

    football = question_role("FOOTBALL_MATCH")
    assert football.primary_use is None
    assert football.status.startswith("PROJECT_ADAPTATION_REQUIRED")
    assert [row["id"] for row in football.football_adaptation["candidate_protocols"]] == [
        "L-F1_SHI_YING",
        "L-F2_ZISUN_GUANGUI",
    ]


def test_liuyao_packet_integrity_and_schema() -> None:
    packet = build_liuyao_packet(
        question="測試六爻來源與裝卦。",
        line_values=[9, 7, 9, 6, 7, 6],
        event_at=_event(),
        timezone_name="Asia/Taipei",
        question_category="GENERAL",
    )
    assert verify_liuyao_packet_integrity(packet)
    errors = sorted(VALIDATOR.iter_errors(packet), key=lambda error: list(error.path))
    assert not errors, "\n".join(error.message for error in errors)

    tampered = dict(packet)
    tampered["question"] = dict(packet["question"])
    tampered["question"]["text"] = "被修改"
    assert not verify_liuyao_packet_integrity(tampered)


def test_invalid_line_values_are_rejected() -> None:
    try:
        cast_liuyao([7, 7, 7], _event(), "Asia/Taipei")
    except ValueError as exc:
        assert "六次" in str(exc)
    else:
        raise AssertionError("少於六爻應拒絕")

    try:
        cast_liuyao([7, 7, 5, 7, 7, 7], _event(), "Asia/Taipei")
    except ValueError as exc:
        assert "6/7/8/9" in str(exc)
    else:
        raise AssertionError("非法爻值應拒絕")
