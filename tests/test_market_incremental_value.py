from datetime import datetime, timedelta, timezone

import pytest

from jarvis.research import (
    MarketBenchmarkSnapshot,
    MarketIncrementalObservation,
    ModelForecast,
    apply_market_incremental_fit,
    fit_market_incremental_value,
    logarithmic_pool,
)


def _observations(count: int = 50):
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    rows = []
    for index in range(count):
        event_at = start + timedelta(days=index)
        actual = ("HOME", "DRAW", "AWAY")[index % 3]
        market_probabilities = {
            "HOME": (0.65, 0.20, 0.15),
            "DRAW": (0.20, 0.60, 0.20),
            "AWAY": (0.15, 0.20, 0.65),
        }[actual]
        structural = (0.34, 0.33, 0.33)
        market = MarketBenchmarkSnapshot(
            source="synthetic-book",
            captured_at=event_at - timedelta(hours=12),
            home_decimal_odds=1.0 / market_probabilities[0] * 1.05,
            draw_decimal_odds=1.0 / market_probabilities[1] * 1.05,
            away_decimal_odds=1.0 / market_probabilities[2] * 1.05,
        )
        rows.append(
            MarketIncrementalObservation(
                match_id=f"M{index}",
                event_at=event_at,
                cutoff_at=event_at - timedelta(hours=6),
                model_family="M0_FOOTBALL",
                model_version="test-v1",
                model_probabilities=structural,
                market_snapshot=market,
                actual_result=actual,
            )
        )
    return rows


def _forecast() -> ModelForecast:
    return ModelForecast(
        match_id="T1",
        model_family="M0_FOOTBALL",
        model_version="test-v1",
        home_win_probability=0.34,
        draw_probability=0.33,
        away_win_probability=0.33,
        expected_home_goals=1.2,
        expected_away_goals=1.0,
        score_grid=((1, 0, 0.4), (1, 1, 0.3), (0, 1, 0.3)),
    )


def test_market_only_is_selected_when_structural_model_adds_no_value():
    fit = fit_market_incremental_value(
        _observations(),
        structural_weight_grid=(0.0, 0.5, 1.0),
        min_matches=50,
    )
    assert fit.selected_structural_weight == 0.0
    assert fit.adds_incremental_value is False
    assert fit.validation_matches == 50
    assert len(fit.artifact_sha256) == 64
    assert fit.candidates[0].mean_log_loss < fit.candidates[-1].mean_log_loss


def test_weight_grid_requires_market_and_model_only_endpoints():
    with pytest.raises(ValueError, match="包含 0"):
        fit_market_incremental_value(
            _observations(),
            structural_weight_grid=(0.5, 1.0),
            min_matches=50,
        )
    with pytest.raises(ValueError, match="包含 1"):
        fit_market_incremental_value(
            _observations(),
            structural_weight_grid=(0.0, 0.5),
            min_matches=50,
        )


def test_validation_rejects_market_snapshot_after_cutoff():
    row = _observations(1)[0]
    late_market = MarketBenchmarkSnapshot(
        source=row.market_snapshot.source,
        captured_at=row.cutoff_at + timedelta(minutes=1),
        home_decimal_odds=row.market_snapshot.home_decimal_odds,
        draw_decimal_odds=row.market_snapshot.draw_decimal_odds,
        away_decimal_odds=row.market_snapshot.away_decimal_odds,
    )
    invalid = MarketIncrementalObservation(
        match_id=row.match_id,
        event_at=row.event_at,
        cutoff_at=row.cutoff_at,
        model_family=row.model_family,
        model_version=row.model_version,
        model_probabilities=row.model_probabilities,
        market_snapshot=late_market,
        actual_result=row.actual_result,
    )
    with pytest.raises(ValueError, match="leakage"):
        fit_market_incremental_value((invalid,), min_matches=1)


def test_log_pool_endpoints_and_apply_are_deterministic():
    structural = (0.5, 0.3, 0.2)
    market = (0.4, 0.35, 0.25)
    assert logarithmic_pool(structural, market, 0.0) == pytest.approx(market)
    assert logarithmic_pool(structural, market, 1.0) == pytest.approx(structural)

    fit = fit_market_incremental_value(
        _observations(),
        structural_weight_grid=(0.0, 1.0),
        min_matches=50,
    )
    event_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    snapshot = MarketBenchmarkSnapshot(
        source="synthetic-book",
        captured_at=event_at - timedelta(hours=12),
        home_decimal_odds=2.0,
        draw_decimal_odds=3.5,
        away_decimal_odds=4.0,
    )
    result = apply_market_incremental_fit(
        _forecast(),
        snapshot,
        fit,
        cutoff_at=event_at - timedelta(hours=6),
    )
    assert result == pytest.approx(snapshot.de_vig_probabilities())
