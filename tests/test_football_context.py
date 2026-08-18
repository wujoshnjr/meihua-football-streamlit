from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from jarvis.football.context import (
    FOOTBALL_CONTEXT_FAMILY,
    FOOTBALL_CONTEXT_VERSION,
    build_context_residual_observation,
    build_fixture_context_snapshot,
    fixture_context_numeric_features,
)
from jarvis.football.strength import DynamicStrengthObservation


TZ = ZoneInfo("UTC")


def _row(
    match_id: str,
    when: datetime,
    home: str,
    away: str,
    *,
    available_delay_hours: int = 2,
) -> DynamicStrengthObservation:
    return DynamicStrengthObservation(
        match_id=match_id,
        event_at=when,
        available_at=when + timedelta(hours=available_delay_hours),
        home_team_id=home,
        away_team_id=away,
        home_goals=1,
        away_goals=0,
        baseline_home_goals_per_match=1.45,
        baseline_away_goals_per_match=1.15,
        source_payload_sha256="a" * 64,
    )


def test_fixture_context_uses_only_rows_available_before_cutoff():
    cutoff = datetime(2026, 8, 10, 18, tzinfo=TZ)
    rows = (
        _row("old-home", cutoff - timedelta(days=3), "HOME", "X"),
        _row("old-away", cutoff - timedelta(days=6), "Y", "AWAY"),
        _row(
            "late-source",
            cutoff - timedelta(days=1),
            "HOME",
            "Z",
            available_delay_hours=48,
        ),
        _row("future", cutoff + timedelta(hours=1), "HOME", "AWAY"),
    )

    snapshot = build_fixture_context_snapshot(
        rows,
        cutoff_at=cutoff,
        home_team_id="HOME",
        away_team_id="AWAY",
    )

    assert snapshot.selected_match_ids == ("old-away", "old-home")
    assert snapshot.home_previous_match_at == cutoff - timedelta(days=3)
    assert snapshot.away_previous_match_at == cutoff - timedelta(days=6)
    assert snapshot.home_rest_hours == pytest.approx(72.0)
    assert snapshot.away_rest_hours == pytest.approx(144.0)
    assert snapshot.home_matches_last_7d == 1
    assert snapshot.away_matches_last_7d == 1


def test_context_features_encode_facts_without_manual_direction():
    cutoff = datetime(2026, 8, 10, 18, tzinfo=TZ)
    snapshot = build_fixture_context_snapshot(
        (
            _row("home", cutoff - timedelta(hours=72), "HOME", "X"),
            _row("away", cutoff - timedelta(days=7), "Y", "AWAY"),
        ),
        cutoff_at=cutoff,
        home_team_id="HOME",
        away_team_id="AWAY",
    )

    features = fixture_context_numeric_features(snapshot)

    assert features["home_under_96h"] == 1.0
    assert features["away_under_96h"] == 0.0
    assert features["congestion_balance"] == 1.0
    assert features["rest_history_balance"] == 0.0
    assert features["home_rest_days_capped"] == pytest.approx(3.0)
    assert features["away_rest_days_capped"] == pytest.approx(7.0)
    assert features["rest_days_difference"] == pytest.approx(-4.0)
    assert all(isinstance(value, float) for value in features.values())


def test_unknown_prior_history_is_explicit_without_constant_one_flags():
    cutoff = datetime(2026, 8, 10, 18, tzinfo=TZ)
    snapshot = build_fixture_context_snapshot(
        (),
        cutoff_at=cutoff,
        home_team_id="HOME",
        away_team_id="AWAY",
    )
    features = fixture_context_numeric_features(snapshot)

    assert snapshot.home_rest_hours is None
    assert snapshot.away_rest_hours is None
    assert features["rest_history_balance"] == 0.0
    assert features["home_rest_days_capped"] == 0.0
    assert features["away_rest_days_capped"] == 0.0
    assert features["home_under_96h"] == 0.0
    assert features["away_under_96h"] == 0.0
    assert "home_rest_known" not in features
    assert "away_rest_known" not in features
    assert "both_rest_known" not in features


def test_context_adapts_to_shared_residual_engine():
    cutoff = datetime(2026, 8, 10, 18, tzinfo=TZ)
    event_at = cutoff + timedelta(hours=6)
    snapshot = build_fixture_context_snapshot(
        (_row("history", cutoff - timedelta(days=4), "HOME", "X"),),
        cutoff_at=cutoff,
        home_team_id="HOME",
        away_team_id="AWAY",
    )

    observation = build_context_residual_observation(
        snapshot,
        match_id="target",
        event_at=event_at,
        baseline_home_lambda=1.4,
        baseline_away_lambda=1.1,
        actual_home_goals=2,
        actual_away_goals=1,
    )

    assert observation.feature_family == FOOTBALL_CONTEXT_FAMILY
    assert observation.feature_schema_version == FOOTBALL_CONTEXT_VERSION
    assert observation.features == fixture_context_numeric_features(snapshot)
    assert observation.validate() == []


def test_context_rejects_duplicate_history_ids():
    cutoff = datetime(2026, 8, 10, 18, tzinfo=TZ)
    row = _row("duplicate", cutoff - timedelta(days=3), "HOME", "X")
    with pytest.raises(ValueError, match="重複 match_id"):
        build_fixture_context_snapshot(
            (row, row),
            cutoff_at=cutoff,
            home_team_id="HOME",
            away_team_id="AWAY",
        )
