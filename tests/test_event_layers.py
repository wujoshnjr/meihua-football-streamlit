from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pytest

from jarvis.case_bundle import build_divination_case_bundle
from jarvis.divination_packet import build_meihua_packet, build_qimen_packet
from jarvis.event_layers import (
    audit_case_collision,
    build_football_event_identity,
)


def _event() -> datetime:
    return datetime(2026, 8, 22, 15, 0, tzinfo=ZoneInfo("Europe/London"))


def _fixture(home: str, away: str) -> dict[str, object]:
    return {
        "competition": "Premier League",
        "season": "2026-27",
        "home_official_name": home,
        "away_official_name": away,
        "scheduled_kickoff_utc": _event().astimezone(timezone.utc),
    }


def _packets(
    *,
    home_display: str,
    away_display: str,
    fixture: dict[str, object] | None,
    coaches: dict[str, str] | None = None,
):
    qimen = build_qimen_packet(
        question="正規時間勝負與候選比分如何？",
        event_at=_event(),
        timezone_name="Europe/London",
        category="football_match",
        home_team=home_display,
        away_team=away_display,
        fixture_identity=fixture,
        coach_identity=coaches,
    )
    meihua = build_meihua_packet(
        question="不判比分，分析初中末段結構與反證。",
        event_at=_event(),
        timezone_name="Europe/London",
        category="football_match",
        home_team=home_display,
        away_team=away_display,
        fixture_identity=fixture,
    )
    return qimen, meihua


def test_event_identity_is_normalized_deterministic_and_prematch_only() -> None:
    first = build_football_event_identity(
        {
            "competition": " Premier   League ",
            "season": "2026-27",
            "home_official_name": "Newcastle United",
            "away_official_name": "Liverpool",
            "scheduled_kickoff_utc": "2026-08-22T14:00:00Z",
        }
    )
    second = build_football_event_identity(
        {
            "competition": "premier league",
            "season": "2026-27",
            "home_official_name": " NEWCASTLE UNITED ",
            "away_official_name": "LIVERPOOL",
            "scheduled_kickoff_utc": "2026-08-22T15:00:00+01:00",
        }
    )

    assert first["event_signature_sha256"] == second["event_signature_sha256"]
    assert first["meihua_event_cast"] == second["meihua_event_cast"]
    cast = first["meihua_event_cast"]["cast"]
    assert cast["upper_number"] in range(1, 9)
    assert cast["lower_number"] in range(1, 9)
    assert cast["moving_line"] in range(1, 7)
    assert first["meihua_event_cast"]["authority"].startswith("PROJECT_ADAPTATION")
    serialized = str(first).lower()
    assert "score" not in serialized
    assert "probability" not in serialized


def test_same_time_different_fixture_is_distinguished_only_by_event_layer() -> None:
    q1, m1 = _packets(
        home_display="紐卡索聯",
        away_display="利物浦",
        fixture=_fixture("Newcastle United", "Liverpool"),
        coaches={"home_birth_ganzhi": "甲子", "away_birth_ganzhi": "乙丑"},
    )
    q2, m2 = _packets(
        home_display="葉士域治",
        away_display="桑德蘭",
        fixture=_fixture("Ipswich Town", "Sunderland"),
        coaches={"home_birth_ganzhi": "丙寅", "away_birth_ganzhi": "丁卯"},
    )

    b1 = build_divination_case_bundle(q1, m1)
    b2 = build_divination_case_bundle(q2, m2)
    a1 = b1["differentiation_audit"]
    a2 = b2["differentiation_audit"]

    assert a1["status"] == "EVENT_AND_PARTICIPANT_READY"
    assert a2["status"] == "EVENT_AND_PARTICIPANT_READY"
    assert (
        a1["temporal"]["temporal_signature_sha256"]
        == a2["temporal"]["temporal_signature_sha256"]
    )
    assert a1["event"]["event_signature_sha256"] != a2["event"]["event_signature_sha256"]

    collision = audit_case_collision(b1, b2)
    assert collision["status"] == "TEMPORAL_COLLISION__DISTINGUISHED_BY_EVENT_LAYER"
    assert collision["same_temporal_signature"] is True
    assert collision["same_event_signature"] is False


def test_same_time_without_event_identity_is_explicitly_unsafe() -> None:
    q1, m1 = _packets(
        home_display="紐卡索聯",
        away_display="利物浦",
        fixture=None,
    )
    q2, m2 = _packets(
        home_display="葉士域治",
        away_display="桑德蘭",
        fixture=None,
    )

    b1 = build_divination_case_bundle(q1, m1)
    b2 = build_divination_case_bundle(q2, m2)

    assert (
        b1["differentiation_audit"]["status"]
        == "TEMPORAL_ONLY__UNSAFE_FOR_CROSS_FIXTURE_DIFFERENTIATION"
    )
    collision = audit_case_collision(b1, b2)
    assert collision["status"] == "UNSAFE_TEMPORAL_COLLISION__EVENT_IDENTITY_MISSING"


def test_coach_year_life_layer_is_auditable_project_adaptation() -> None:
    qimen, meihua = _packets(
        home_display="A隊",
        away_display="B隊",
        fixture=_fixture("Team A", "Team B"),
        coaches={"home_birth_ganzhi": "甲子", "away_birth_ganzhi": "辛酉"},
    )
    participant = qimen["participant_layer"]

    assert participant["status"] == "READY"
    assert participant["authority"] == "PROJECT_ADAPTATION__COACH_AS_MATCH_ACTOR"
    assert participant["home"]["birth_year_ganzhi"] == "甲子"
    assert participant["home"]["year_stem"] == "甲"
    assert participant["home"]["year_branch"] == "子"
    assert participant["home"]["placement_basis"] == "BIRTH_YEAR_STEM_ON_HEAVEN_PLATE__BRANCH_RETAINED_FOR_IDENTITY_ONLY"
    assert "不等同完整古法年命演算法" in participant["method_boundary"]
    assert participant["away"]["birth_year_ganzhi"] == "辛酉"
    assert participant["home"]["palace"] in range(1, 10)
    assert participant["away"]["palace"] in range(1, 10)
    assert len(participant["participant_signature_sha256"]) == 64

    bundle = build_divination_case_bundle(qimen, meihua)
    assert bundle["differentiation_audit"]["participant"]["status"] == "READY"


def test_bundle_rejects_qimen_meihua_event_identity_mismatch() -> None:
    qimen, _ = _packets(
        home_display="A隊",
        away_display="B隊",
        fixture=_fixture("Team A", "Team B"),
    )
    _, meihua = _packets(
        home_display="A隊",
        away_display="B隊",
        fixture=_fixture("Team A", "Team C"),
    )

    with pytest.raises(ValueError, match="EVENT_IDENTITY_LAYER_MISMATCH"):
        build_divination_case_bundle(qimen, meihua)


def test_invalid_coach_ganzhi_is_rejected_before_interpretation() -> None:
    with pytest.raises(ValueError, match="出生年干支"):
        _packets(
            home_display="A隊",
            away_display="B隊",
            fixture=_fixture("Team A", "Team B"),
            coaches={"home_birth_ganzhi": "2020", "away_birth_ganzhi": "辛酉"},
        )
