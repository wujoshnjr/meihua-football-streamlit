from datetime import datetime
from zoneinfo import ZoneInfo

from jarvis.divination_packet import DIVINATION_PACKET_VERSION, build_meihua_packet
from jarvis.zhouyi import zhouyi_catalog_stats, zhouyi_hexagram


def _event() -> datetime:
    return datetime(2026, 6, 15, 12, 0, tzinfo=ZoneInfo("America/New_York"))


def test_zhouyi_corpus_exposes_complete_64_384_contract():
    stats = zhouyi_catalog_stats()
    assert stats["materialized_hexagrams"] == 64
    assert stats["expected_hexagrams"] == 64
    assert stats["materialized_standard_lines"] == 384
    assert stats["expected_standard_lines"] == 384
    assert len(zhouyi_hexagram(1)["lines"]) == 6
    assert len(zhouyi_hexagram(64)["lines"]) == 6
    assert zhouyi_hexagram(1)["guaci"]["classical_text"]
    assert zhouyi_hexagram(64)["tuan"]["classical_text"]


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
    assert review["original"]["guaci"]["classical_text"]
    assert review["original"]["tuan"]["classical_text"]
    assert review["original"]["xiang"]["classical_text"]
    assert review["moving_line"]["classical_text"]
    assert review["moving_line"]["source_page_start"]
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
    serialized = str(packet).lower()
    assert "home_win_probability" not in serialized
    assert "fixed_score" not in serialized
