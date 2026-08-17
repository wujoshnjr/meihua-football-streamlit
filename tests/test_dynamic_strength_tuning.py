from datetime import datetime, timedelta, timezone

import pytest

from jarvis.football import (
    DynamicStrengthObservation,
    DynamicStrengthValidationFixture,
    tune_dynamic_strength,
)


def _history():
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    teams = ("A", "B", "C", "D")
    rows = []
    for index in range(120):
        home = teams[index % 4]
        away = teams[(index + 1) % 4]
        # A looks like an elite finisher in realized goals, but its xG process is neutral.
        home_goals = 3 if home == "A" else 1
        away_goals = 3 if away == "A" else 1
        event_at = start + timedelta(days=index)
        rows.append(
            DynamicStrengthObservation(
                match_id=f"H{index}",
                event_at=event_at,
                available_at=event_at + timedelta(hours=3),
                home_team_id=home,
                away_team_id=away,
                home_goals=home_goals,
                away_goals=away_goals,
                baseline_home_goals_per_match=1.0,
                baseline_away_goals_per_match=1.0,
                source_payload_sha256="a" * 64,
                home_xg=1.0,
                away_xg=1.0,
            )
        )
    return rows


def _validation():
    start = datetime(2024, 5, 5, tzinfo=timezone.utc)
    fixtures = []
    for index in range(4):
        event_at = start + timedelta(days=index * 3)
        fixtures.append(
            DynamicStrengthValidationFixture(
                match_id=f"V{index}",
                event_at=event_at,
                cutoff_at=event_at - timedelta(hours=6),
                home_team_id="A" if index % 2 == 0 else "B",
                away_team_id="B" if index % 2 == 0 else "A",
                baseline_home_goals_per_match=1.0,
                baseline_away_goals_per_match=1.0,
                actual_home_goals=1,
                actual_away_goals=1,
            )
        )
    return fixtures


def test_validation_tuning_can_select_xg_when_goals_are_noisy():
    result = tune_dynamic_strength(
        _history(),
        _validation(),
        half_life_days_grid=(365.0,),
        l2_penalty_grid=(2.0,),
        xg_weight_grid=(0.0, 1.0),
        min_matches=80,
    )
    assert result.selected_xg_weight == 1.0
    assert result.validation_matches == 4
    assert len(result.candidates) == 2
    assert len(result.artifact_sha256) == 64
    assert result.candidates[0].mean_log_loss < result.candidates[1].mean_log_loss


def test_tuning_requires_goals_only_fallback():
    with pytest.raises(ValueError, match="包含 0"):
        tune_dynamic_strength(
            _history(),
            _validation(),
            half_life_days_grid=(180.0,),
            l2_penalty_grid=(8.0,),
            xg_weight_grid=(0.5, 1.0),
            min_matches=80,
        )


def test_tuning_rejects_non_validation_labels():
    fixture = _validation()[0]
    invalid = DynamicStrengthValidationFixture(
        match_id=fixture.match_id,
        event_at=fixture.event_at,
        cutoff_at=fixture.cutoff_at,
        home_team_id=fixture.home_team_id,
        away_team_id=fixture.away_team_id,
        baseline_home_goals_per_match=fixture.baseline_home_goals_per_match,
        baseline_away_goals_per_match=fixture.baseline_away_goals_per_match,
        actual_home_goals=fixture.actual_home_goals,
        actual_away_goals=fixture.actual_away_goals,
        dataset_role="TEST_UNTOUCHED",  # type: ignore[arg-type]
    )
    with pytest.raises(ValueError, match="不是 VALIDATION"):
        tune_dynamic_strength(
            _history(),
            (invalid,),
            half_life_days_grid=(180.0,),
            l2_penalty_grid=(8.0,),
            xg_weight_grid=(0.0,),
            min_matches=80,
        )


def test_tuning_is_deterministic():
    kwargs = dict(
        half_life_days_grid=(180.0, 365.0),
        l2_penalty_grid=(2.0,),
        xg_weight_grid=(0.0, 1.0),
        min_matches=80,
    )
    first = tune_dynamic_strength(_history(), _validation(), **kwargs)
    second = tune_dynamic_strength(reversed(_history()), reversed(_validation()), **kwargs)
    assert first.to_dict() == second.to_dict()
