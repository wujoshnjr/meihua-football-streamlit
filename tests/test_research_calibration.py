from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from jarvis.research.calibration import (
    RESEARCH_CALIBRATION_VERSION,
    apply_research_calibration,
    fit_research_calibration,
)
from jarvis.research.experiment import ModelForecast


@dataclass(frozen=True)
class _Record:
    match_id: str
    event_at: datetime
    dataset_role: str
    actual_home_goals: int
    actual_away_goals: int


@dataclass(frozen=True)
class _Row:
    record: _Record
    fingerprint_sha256: str


def _forecast(match_id: str, probabilities: tuple[float, float, float]) -> ModelForecast:
    return ModelForecast(
        match_id=match_id,
        model_family="M0_FOOTBALL",
        model_version="research-football-v1",
        home_win_probability=probabilities[0],
        draw_probability=probabilities[1],
        away_win_probability=probabilities[2],
        expected_home_goals=1.5,
        expected_away_goals=1.0,
        score_grid=((1, 0, 0.5), (1, 1, 0.3), (0, 1, 0.2)),
        artifact_sources=("football-fit:abc",),
    )


def _rows_and_forecasts():
    timezone = ZoneInfo("Asia/Taipei")
    start = datetime(2025, 1, 1, 20, 0, tzinfo=timezone)
    rows = []
    forecasts = []
    outcomes = ["HOME", "DRAW", "AWAY", "HOME", "DRAW", "AWAY"]
    for index, outcome in enumerate(outcomes):
        match_id = f"cal-{index}"
        goals = {"HOME": (1, 0), "DRAW": (1, 1), "AWAY": (0, 1)}[outcome]
        rows.append(
            _Row(
                record=_Record(match_id, start + timedelta(days=index), "CALIBRATION", *goals),
                fingerprint_sha256=f"{index + 1:064x}",
            )
        )
        # Deliberately overconfident HOME probabilities: temperature > 1 should help
        # once all three outcomes are represented equally.
        forecasts.append(_forecast(match_id, (0.80, 0.10, 0.10)))

    # A TEST_UNTOUCHED label that would favour the overconfident forecast must never
    # participate in calibration fitting.
    rows.append(
        _Row(
            record=_Record("test-0", start + timedelta(days=20), "TEST_UNTOUCHED", 2, 0),
            fingerprint_sha256="f" * 64,
        )
    )
    forecasts.append(_forecast("test-0", (0.80, 0.10, 0.10)))
    return rows, forecasts


def test_research_calibration_uses_only_calibration_rows_and_preserves_score_grid():
    rows, forecasts = _rows_and_forecasts()
    bundle = fit_research_calibration(
        iter(rows),
        iter(forecasts),
        model_family="M0_FOOTBALL",
        min_matches=6,
        grid_steps=301,
    )

    assert bundle.temperature_fit.matches == 6
    assert bundle.temperature_fit.post_log_loss < bundle.temperature_fit.pre_log_loss
    assert bundle.applied_temperature > 1.0

    untouched = next(item for item in forecasts if item.match_id == "test-0")
    calibrated = apply_research_calibration(untouched, bundle)

    assert calibrated.score_grid == untouched.score_grid
    assert calibrated.expected_home_goals == untouched.expected_home_goals
    assert calibrated.expected_away_goals == untouched.expected_away_goals
    assert calibrated.home_win_probability < untouched.home_win_probability
    assert abs(
        calibrated.home_win_probability
        + calibrated.draw_probability
        + calibrated.away_win_probability
        - 1.0
    ) < 1e-12
    assert calibrated.artifact_sources[-1].startswith("temperature-fit:")
    assert RESEARCH_CALIBRATION_VERSION in calibrated.model_version


def test_research_calibration_rejects_model_version_drift():
    rows, forecasts = _rows_and_forecasts()
    bundle = fit_research_calibration(
        rows,
        forecasts,
        model_family="M0_FOOTBALL",
        min_matches=6,
        grid_steps=301,
    )
    drifted = ModelForecast(
        **{
            **forecasts[-1].__dict__,
            "model_version": "different-football-v2",
        }
    )

    with pytest.raises(ValueError, match="model_version"):
        apply_research_calibration(drifted, bundle)
