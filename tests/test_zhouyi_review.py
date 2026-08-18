from datetime import datetime
from zoneinfo import ZoneInfo

from jarvis.divination_packet import DIVINATION_PACKET_VERSION, build_meihua_packet
from jarvis.zhouyi import (
    zhouyi_catalog_stats,
    zhouyi_hexagram,
    zhouyi_line_semantic_profile,
)


def _event() -> datetime:
    return datetime(2026, 6, 15, 12, 0, tzinfo=ZoneInfo("America/New_York"))


def test_zhouyi_corpus_exposes_complete_64_384_contract():
    stats = zhouyi_catalog_stats()
    assert stats["materialized_shards"] == stats["expected_shards"] == 8
    assert stats["materialized_hexagrams"] == stats["expected_hexagrams"] == 64
    assert stats["materialized_standard_lines"] == stats["expected_standard_lines"] == 384
    assert stats["mapped_xiaoxiang"] == 378
    assert stats["grouped_qian_xiaoxiang"] == 6
    assert stats["semantic_atoms"] >= 20
    assert stats["judgment_markers"] >= 7
    assert len(zhouyi_hexagram(1)["lines"]) == 6
    assert len(zhouyi_hexagram(64)["lines"]) == 6
    assert zhouyi_hexagram(1)["guaci"]["classical_text"]
    assert zhouyi_hexagram(64)["tuan"]["classical_text"]


def test_qian_source_exception_is_explicit_and_not_fabricated():
    first_line = zhouyi_hexagram(1)["lines"][0]
    assert first_line["marker"] == "初九"
    assert "潛龍勿用" in first_line["classical_text"]
    assert first_line["xiaoxiang"]["status"] == "GROUPED_IN_QIAN_XIANG_BLOCK"
    assert first_line["xiaoxiang"]["classical_text"] is None
    profile = zhouyi_line_semantic_profile(first_line)
    ids = {row["id"] for row in profile["semantic_atoms"]}
    assert "concealment_uncertainty" in ids
    assert "restraint_wait" in ids


def test_weiji_first_line_has_mapped_xiaoxiang_and_text_grounded_semantics():
    first_line = zhouyi_hexagram(64)["lines"][0]
    assert first_line["marker"] == "初六"
    assert "濡其尾" in first_line["classical_text"]
    assert first_line["xiaoxiang"]["status"] == "MAPPED"
    assert first_line["xiaoxiang"]["classical_text"]
    profile = zhouyi_line_semantic_profile(first_line)
    marker_ids = {row["id"] for row in profile["judgment_markers"]}
    atom_ids = {row["id"] for row in profile["semantic_atoms"]}
    assert "difficulty" in marker_ids
    assert "water_wet_risk" in atom_ids
    assert profile["observable_signals"]
    assert profile["counter_signals"]
    assert profile["inference_status"] == "PROJECT_HEURISTIC__NOT_CLASSICAL_COMMENTARY"


def test_meihua_packet_v2_contains_actual_moving_line_classical_text_and_source_audit():
    packet = build_meihua_packet(
        question="西班牙對維德角，這場比賽整體走勢如何？",
        event_at=_event(),
        timezone_name="America/New_York",
        category="football_match",
        home_team="西班牙",
        away_team="維德角",
    )
    assert packet["schema_version"] == DIVINATION_PACKET_VERSION == "DIVINATION_PACKET_V2"
    review = packet["zhouyi_review"]
    assert review["status"] == "SOURCE_AWARE_REVIEW_READY"
    assert review["source_audit"]["all_core_alignments_match"] is True
    assert review["source_audit"]["moving_line_matches_snapshot"] is True
    assert review["source_audit"]["moving_line_xiaoxiang_status"] in {"MAPPED", "GROUPED_IN_QIAN_XIANG_BLOCK"}
    assert review["original"]["guaci"]["classical_text"]
    assert review["original"]["tuan"]["classical_text"]
    assert review["original"]["xiang"]["classical_text"]
    assert review["moving_line"]["classical_text"]
    assert review["moving_line"]["source_page_start"]
    assert review["moving_line"]["semantic_profile"]["text_basis"]["line_classical_text"]
    assert review["review_dimensions"]
    assert review["football_meaning_contract"]["forbidden_shortcuts"]
    assert packet["event"]["normalization"] == "ACTUAL_CAST_EVENT_LOCAL_TIME"


def test_zhouyi_review_keeps_classical_and_project_meaning_separate():
    packet = build_meihua_packet(
        question="測試",
        event_at=_event(),
        timezone_name="America/New_York",
    )
    line = packet["zhouyi_review"]["moving_line"]
    assert line["classical_text"]
    assert line["project_general"]
    assert line["football_modern_application"]
    assert "古籍原文" in line["boundary"]
    assert "不是《周易》原註" in line["semantic_profile"]["boundary"]
    serialized = str(packet).lower()
    assert "home_win_probability" not in serialized
    assert "fixed_score" not in serialized
