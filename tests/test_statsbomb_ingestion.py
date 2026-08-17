from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from jarvis.data.statsbomb import parse_statsbomb_historical_match


MATCH = {
    "match_id": 123,
    "match_date": "2026-01-10",
    "kick_off": "20:00:00.000",
    "competition": {"competition_name": "Test League"},
    "home_team": {"home_team_id": 1, "home_team_name": "Home"},
    "away_team": {"away_team_id": 2, "away_team_name": "Away"},
    "home_score": 2,
    "away_score": 1,
}

EVENTS = [
    {
        "period": 1,
        "type": {"name": "Shot"},
        "team": {"id": 1, "name": "Home"},
        "shot": {"statsbomb_xg": 0.4},
    },
    {
        "period": 2,
        "type": {"name": "Shot"},
        "team": {"id": 1, "name": "Home"},
        "shot": {"statsbomb_xg": 0.6},
    },
    {
        "period": 2,
        "type": {"name": "Shot"},
        "team": {"id": 2, "name": "Away"},
        "shot": {"statsbomb_xg": 0.7},
    },
]


def test_parse_normal_time_match_and_xg():
    row = parse_statsbomb_historical_match(
        MATCH,
        EVENTS,
        timezone_name="Asia/Taipei",
        available_at=datetime(2026, 1, 11, 0, tzinfo=ZoneInfo("Asia/Taipei")),
    )
    assert row.match_id == "123"
    assert row.event_at.hour == 20
    assert row.home_goals == 2
    assert row.away_goals == 1
    assert row.home_xg == pytest.approx(1.0)
    assert row.away_xg == pytest.approx(0.7)
    historical = row.to_historical_match()
    assert historical.home_xg == pytest.approx(1.0)
    assert historical.available_at == row.available_at


def test_extra_time_requires_registered_90_minute_override():
    events = [*EVENTS, {"period": 3, "type": {"name": "Half Start"}, "team": {"id": 1}}]
    available_at = datetime(2026, 1, 11, 0, tzinfo=ZoneInfo("Asia/Taipei"))
    with pytest.raises(ValueError, match="normal_time_score_override"):
        parse_statsbomb_historical_match(
            MATCH,
            events,
            timezone_name="Asia/Taipei",
            available_at=available_at,
        )
    row = parse_statsbomb_historical_match(
        MATCH,
        events,
        timezone_name="Asia/Taipei",
        available_at=available_at,
        normal_time_score_override=(1, 1),
    )
    assert (row.home_goals, row.away_goals) == (1, 1)
    assert row.home_xg == pytest.approx(1.0)


def test_extra_time_shots_do_not_enter_normal_time_xg():
    events = [
        *EVENTS,
        {
            "period": 3,
            "type": {"name": "Shot"},
            "team": {"id": 1, "name": "Home"},
            "shot": {"statsbomb_xg": 0.9},
        },
    ]
    row = parse_statsbomb_historical_match(
        MATCH,
        events,
        timezone_name="Asia/Taipei",
        available_at=datetime(2026, 1, 11, 0, tzinfo=ZoneInfo("Asia/Taipei")),
        normal_time_score_override=(2, 1),
    )
    assert row.home_xg == pytest.approx(1.0)


def test_available_at_cannot_precede_match():
    with pytest.raises(ValueError, match="available_at 不可早於 event_at"):
        parse_statsbomb_historical_match(
            MATCH,
            EVENTS,
            timezone_name="Asia/Taipei",
            available_at=datetime(2026, 1, 10, 19, tzinfo=ZoneInfo("Asia/Taipei")),
        )
