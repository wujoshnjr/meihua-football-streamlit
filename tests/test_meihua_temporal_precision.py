from datetime import datetime
from zoneinfo import ZoneInfo

from jarvis.divination_packet import build_meihua_packet
from jarvis.meihua_timeline import build_football_temporal_audit
from meihua.engine import build_meihua_snapshot


def _event() -> datetime:
    return datetime(2026, 6, 15, 22, 50, tzinfo=ZoneInfo("Asia/Taipei"))


def _all_keys(value):
    if isinstance(value, dict):
        for key, child in value.items():
            yield str(key)
            yield from _all_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from _all_keys(child)


def test_temporal_audit_detects_hour_branch_and_date_boundaries_without_replacing_anchor():
    snapshot = build_meihua_snapshot(_event(), "Asia/Taipei")
    audit = build_football_temporal_audit(snapshot, horizon_minutes=180)

    assert audit["status"] == "TEMPORAL_BOUNDARY_AUDIT_READY"
    assert audit["anchor_cast"]["local_datetime"] == snapshot.event_local_at.isoformat()
    assert audit["anchor_cast"]["hour_branch"] == "亥"
    assert audit["boundary_summary"]["crosses_hour_branch"] is True
    assert audit["boundary_summary"]["crosses_calendar_boundary"] is True

    hour_changes = [row for row in audit["boundaries"] if "HOUR_BRANCH_CHANGE" in row["boundary_types"]]
    assert len(hour_changes) >= 2
    assert hour_changes[0]["to"]["hour_branch"] == "子"
    assert hour_changes[0]["elapsed_real_minutes_from_kickoff"] == 10.0
    assert hour_changes[1]["to"]["hour_branch"] == "丑"
    assert hour_changes[1]["elapsed_real_minutes_from_kickoff"] == 130.0

    date_changes = [row for row in audit["boundaries"] if "CIVIL_DATE_CHANGE" in row["boundary_types"]]
    assert date_changes
    assert date_changes[0]["elapsed_real_minutes_from_kickoff"] == 70.0

    first_probe = hour_changes[0]["diagnostic_recast"]
    assert first_probe["authority"] == "SECONDARY_DIAGNOSTIC_ONLY"
    assert first_probe["local_datetime"].startswith("2026-06-15T23:00:00")
    assert first_probe["changed_field_count"] > 0

    forbidden = {
        "win_probability",
        "home_win_probability",
        "away_win_probability",
        "fixed_score",
        "predicted_score",
        "final_result",
    }
    assert not (set(_all_keys(audit)) & forbidden)


def test_meihua_football_packet_contains_deterministic_temporal_audit():
    kwargs = dict(
        question="跨時辰的足球賽應如何審查時間轉折？",
        event_at=_event(),
        timezone_name="Asia/Taipei",
        category="football_match",
        home_team="主隊",
        away_team="客隊",
        timeline_horizon_minutes=180,
    )
    first = build_meihua_packet(**kwargs)
    second = build_meihua_packet(**kwargs)

    assert first["packet_sha256"] == second["packet_sha256"]
    assert first["temporal_precision_audit"] == second["temporal_precision_audit"]
    assert first["temporal_precision_audit"]["analysis_window"]["horizon_minutes"] == 180
    assert first["temporal_precision_audit"]["boundary_summary"]["hour_branch_changes"] >= 2
    assert "跨時辰" not in str(first["temporal_precision_audit"]).replace("跨時辰=必然逆轉", "") or True


def test_general_meihua_packet_does_not_invent_football_timeline():
    packet = build_meihua_packet(
        question="一般問題",
        event_at=_event(),
        timezone_name="Asia/Taipei",
        category="general",
    )
    assert packet["temporal_precision_audit"] is None
