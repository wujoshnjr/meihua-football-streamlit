from datetime import datetime, timedelta, timezone

import pytest

from jarvis.football.strength import (
    DynamicStrengthFit,
    DynamicStrengthObservation,
    TeamStrength,
    fit_dynamic_strength,
    predict_dynamic_lambdas,
)


def _synthetic_rows():
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    rows = []
    teams = ("A", "B", "C", "D")
    for index in range(160):
        home = teams[index % 4]
        away = teams[(index + 1) % 4]
        home_goals = 3 if home == "A" else 1
        away_goals = 3 if away == "A" else 1
        event_at = start + timedelta(days=index)
        rows.append(
            DynamicStrengthObservation(
                match_id=f"M{index}",
                event_at=event_at,
                available_at=event_at + timedelta(hours=3),
                home_team_id=home,
                away_team_id=away,
                home_goals=home_goals,
                away_goals=away_goals,
                baseline_home_goals_per_match=1.0,
                baseline_away_goals_per_match=1.0,
                source_payload_sha256="a" * 64,
            )
        )
    return rows


def test_fit_learns_opponent_adjusted_attack_strength():
    cutoff = datetime(2025, 1, 1, tzinfo=timezone.utc)
    fit = fit_dynamic_strength(_synthetic_rows(), cutoff_at=cutoff, half_life_days=365.0, l2_penalty=2.0)
    assert fit.converged
    assert fit.team("A") is not None
    assert fit.team("B") is not None
    assert fit.team("A").attack_multiplier > fit.team("B").attack_multiplier


def test_future_unavailable_rows_are_not_used():
    rows = _synthetic_rows()
    cutoff = datetime(2024, 4, 1, tzinfo=timezone.utc)
    fit = fit_dynamic_strength(rows, cutoff_at=cutoff, min_matches=50)
    assert all(rows[int(match_id[1:])].event_at < cutoff for match_id in fit.selected_match_ids)
    assert fit.matches < len(rows)


def test_zero_effects_reproduce_registered_baseline_and_cold_start():
    fit = DynamicStrengthFit(
        schema_version="test",
        cutoff_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
        half_life_days=180.0,
        l2_penalty=8.0,
        matches=100,
        teams=(TeamStrength("A", 0.0, 0.0, 10.0),),
        converged=True,
        iterations=1,
        selected_match_ids=(),
    )
    prediction = predict_dynamic_lambdas(
        fit,
        home_team_id="A",
        away_team_id="NEW",
        baseline_home_goals_per_match=1.25,
        baseline_away_goals_per_match=1.05,
    )
    assert prediction.home_lambda == pytest.approx(1.25)
    assert prediction.away_lambda == pytest.approx(1.05)
    assert prediction.cold_start_teams == ("NEW",)
