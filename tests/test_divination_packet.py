from datetime import datetime
from zoneinfo import ZoneInfo

from jarvis.divination_packet import (
    DIVINATION_PACKET_VERSION,
    build_meihua_packet,
    build_qimen_packet,
)


def event_at() -> datetime:
    return datetime(2026, 6, 15, 12, 0, tzinfo=ZoneInfo("America/New_York"))


def test_qimen_packet_is_deterministic_and_ai_handoff_only():
    kwargs = dict(
        question="西班牙對維德角，這場比賽整體走勢如何？",
        event_at=event_at(),
        timezone_name="America/New_York",
        category="football_match",
        home_team="西班牙",
        away_team="維德角",
    )
    first = build_qimen_packet(**kwargs)
    second = build_qimen_packet(**kwargs)

    assert first["schema_version"] == DIVINATION_PACKET_VERSION
    assert first["system"] == "QIMEN_DUNJIA"
    assert first["packet_sha256"] == second["packet_sha256"]
    assert first["chart"] == second["chart"]
    assert "generated_at" not in first["chart"]
    assert first["host_guest"]["home_team"] == "西班牙"
    assert first["knowledge_context"]
    kinds = [row["kind"] for row in first["knowledge_context"]]
    assert "qimen_deep_reading_policy" in kinds
    assert kinds.count("qimen_palace_deep_profile") == 9
    deep_palaces = [row for row in first["knowledge_context"] if row["kind"] == "qimen_palace_deep_profile"]
    assert all(row["football_questions"] for row in deep_palaces)
    assert any(row["deity_detail"] for row in deep_palaces)
    serialized = str(first).lower()
    assert "home_win_probability" not in serialized
    assert "fixed_score" not in serialized


def test_meihua_packet_is_deterministic_and_contains_deep_three_hexagram_layers():
    kwargs = dict(
        question="西班牙對維德角，這場比賽整體走勢如何？",
        event_at=event_at(),
        timezone_name="America/New_York",
        category="football_match",
        home_team="西班牙",
        away_team="維德角",
    )
    first = build_meihua_packet(**kwargs)
    second = build_meihua_packet(**kwargs)

    assert first["schema_version"] == DIVINATION_PACKET_VERSION
    assert first["system"] == "MEIHUA_YISHU"
    assert first["packet_sha256"] == second["packet_sha256"]
    assert first["hexagram"] == second["hexagram"]
    kinds = {row["kind"] for row in first["knowledge_context"]}
    assert "meihua_original_hexagram" in kinds
    assert "meihua_mutual_hexagram" in kinds
    assert "meihua_changed_hexagram" in kinds
    assert "meihua_body_use" in kinds
    assert "meihua_moving_line_role" in kinds
    assert "meihua_deep_reading_policy" in kinds
    assert "meihua_deep_profile" in kinds

    deep = next(row for row in first["knowledge_context"] if row["kind"] == "meihua_deep_profile")
    assert deep["original"]["hexagram"]["name"]
    assert deep["mutual"]["hexagram"]["name"]
    assert deep["changed"]["hexagram"]["name"]
    assert deep["body_use"]["relation_detail"]["general"]
    assert deep["moving_line"]["football"]
    assert len(deep["football_dimensions"]) == 8

    serialized = str(first).lower()
    assert "home_win_probability" not in serialized
    assert "fixed_score" not in serialized


def test_football_packets_require_both_teams():
    try:
        build_meihua_packet(
            question="測試",
            event_at=event_at(),
            timezone_name="America/New_York",
            category="football_match",
            home_team="西班牙",
            away_team="",
        )
    except ValueError as exc:
        assert "主隊與客隊" in str(exc)
    else:
        raise AssertionError("football packet must reject missing teams")
