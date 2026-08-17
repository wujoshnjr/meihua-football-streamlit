from datetime import datetime, timedelta, timezone

import pytest

from jarvis.football.strength import (
    DynamicStrengthFit,
    DynamicStrengthObservation,
    TeamStrength,
    fit_dynamic_strength,
    predict_dynamic_lambdas,
)


def _synthetic_rows(*, include_xg=False):
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
                home_xg=float(home_goals) if include_xg else None,
                away_xg=float(away_goals) if include_xg else None,
            )
        )
    return rows


def test_fit_learns_opponent_adjusted_attack_strength_with_zero_sum_constraints():
    cutoff = datetime(2025, 1, 1, tzinfo=timezone.utc)
    fit = fit_dynamic_strength(_synthetic_rows(), cutoff_at=cutoff, half_life_days=365.0, l2_penalty=2.0)
    assert fit.converged
    assert fit.identifiability_constraint == "SUM_TO_ZERO_ATTACK_AND_DEFENCE"
    assert fit.xg_weight == 0.0
    assert fit.target_definition == "GOALS_ONLY"
    assert fit.team("A") is not None
    assert fit.team("B") is not None
    assert fit.team("A").attack_multiplier > fit.team("B").attack_multiplier
    assert sum(team.attack_log_effect for team in fit.teams) == pytest.approx(0.0, abs=1e-10)
    assert sum(team.defence_weakness_log_effect for team in fit.teams) == pytest.approx(0.0, abs=1e-10)


def test_future_unavailable_rows_are_not_used():
    rows = _synthetic_rows()
    cutoff = datetime(2024, 4, 1, tzinfo=timezone.utc)
    fit = fit_dynamic_strength(rows, cutoff_at=cutoff, min_matches=50)
    assert all(rows[int(match_id[1:])].event_at < cutoff for match_id in fit.selected_match_ids)
    assert fit.matches < len(rows)


def test_zero_xg_weight_is_backward_compatible():
    cutoff = datetime(2025, 1, 1, tzinfo=timezone.utc)
    without_xg = fit_dynamic_strength(_synthetic_rows(), cutoff_at=cutoff, xg_weight=0.0)
    with_xg_available = fit_dynamic_strength(
        _synthetic_rows(include_xg=True), cutoff_at=cutoff, xg_weight=0.0
    )
    assert tuple(team.attack_log_effect for team in without_xg.teams) == pytest.approx(
        tuple(team.attack_log_effect for team in with_xg_available.teams)
    )
    assert tuple(team.defence_weakness_log_effect for team in without_xg.teams) == pytest.approx(
        tuple(team.defence_weakness_log_effect for team in with_xg_available.teams)
    )


def test_xg_blend_can_shrink_finishing_noise():
    rows = _synthetic_rows(include_xg=True)
    noisy_rows = []
    for row in rows:
        home_xg = 1.0 if row.home_team_id == "A" else row.home_xg
        away_xg = 1.0 if row.away_team_id == "A" else row.away_xg
        noisy_rows.append(
            DynamicStrengthObservation(
                match_id=row.match_id,
                event_at=row.event_at,
                available_at=row.available_at,
                home_team_id=row.home_team_id,
                away_team_id=row.away_team_id,
                home_goals=row.home_goals,
                away_goals=row.away_goals,
                baseline_home_goals_per_match=row.baseline_home_goals_per_match,
                baseline_away_goals_per_match=row.baseline_away_goals_per_match,
                source_payload_sha256=row.source_payload_sha256,
                home_xg=home_xg,
                away_xg=away_xg,
            )
        )
    cutoff = datetime(2025, 1, 1, tzinfo=timezone.utc)
    goals_fit = fit_dynamic_strength(noisy_rows, cutoff_at=cutoff, xg_weight=0.0)
    xg_fit = fit_dynamic_strength(noisy_rows, cutoff_at=cutoff, xg_weight=1.0)
    assert xg_fit.target_definition == "GOALS_XG_CONVEX_BLEND"
    assert xg_fit.team("A").attack_log_effect < goals_fit.team("A").attack_log_effect


def test_positive_xg_weight_requires_complete_xg_coverage():
    cutoff = datetime(2025, 1, 1, tzinfo=timezone.utc)
    with pytest.raises(ValueError, match="所有 selected rows"):
        fit_dynamic_strength(_synthetic_rows(), cutoff_at=cutoff, xg_weight=0.5)


def test_partial_xg_pair_is_invalid():
    row = _synthetic_rows()[0]
    broken = DynamicStrengthObservation(
        match_id=row.match_id,
        event_at=row.event_at,
        available_at=row.available_at,
        home_team_id=row.home_team_id,
        away_team_id=row.away_team_id,
        home_goals=row.home_goals,
        away_goals=row.away_goals,
        baseline_home_goals_per_match=row.baseline_home_goals_per_match,
        baseline_away_goals_per_match=row.baseline_away_goals_per_match,
        source_payload_sha256=row.source_payload_sha256,
        home_xg=1.2,
        away_xg=None,
    )
    assert any("同時存在" in error for error in broken.validate())


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
