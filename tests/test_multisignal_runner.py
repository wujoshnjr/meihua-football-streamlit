from datetime import datetime, timedelta
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

from jarvis.research.experiment import evaluate_forecast
from jarvis.research.runner import (
    BaselineLambdaSnapshot,
    fit_model_family,
    predict_model_family,
)


TZ = ZoneInfo("UTC")


def _row(index: int, *, role: str = "TRAIN"):
    event_at = datetime(2025, 1, 1, 20, tzinfo=TZ) + timedelta(days=index)
    record = SimpleNamespace(
        match_id=f"m{index}",
        event_at=event_at,
        dataset_role=role,
        actual_home_goals=1 + (index % 2),
        actual_away_goals=index % 2,
        qimen_snapshot=SimpleNamespace(schema_version="qimen-test-v1"),
        meihua_snapshot=SimpleNamespace(schema_version="meihua-test-v1"),
    )
    q_signal = float((index % 5) - 2)
    m_signal = float(((index * index + 3 * index) % 7) - 3)
    return SimpleNamespace(
        record=record,
        fingerprint_sha256=f"{index:064x}"[-64:],
        qimen_numeric_features={"q_signal": q_signal},
        meihua_numeric_features={"m_signal": m_signal},
    )


def _baseline(index: int, *, score_model: str = "INDEPENDENT_POISSON") -> BaselineLambdaSnapshot:
    return BaselineLambdaSnapshot(
        match_id=f"m{index}",
        home_lambda=1.25 + 0.01 * (index % 4),
        away_lambda=0.95 + 0.01 * (index % 3),
        artifact_source="football-baseline:test",
        score_model=score_model,
        dixon_coles_rho=-0.05 if score_model == "DIXON_COLES" else 0.0,
        max_goals=8,
    )


def test_m0_builds_normalized_score_distribution_without_residual():
    row = _row(0)
    forecast = predict_model_family(row, _baseline(0), model_family="M0_FOOTBALL")
    assert forecast.model_family == "M0_FOOTBALL"
    assert sum(cell[2] for cell in forecast.score_grid) == pytest.approx(1.0)
    assert (
        forecast.home_win_probability + forecast.draw_probability + forecast.away_win_probability
        == pytest.approx(1.0)
    )
    assert forecast.artifact_sources == ("football-baseline:test",)


def test_qimen_meihua_and_combined_use_same_generic_residual_engine():
    rows = [_row(index) for index in range(30)]
    baselines = {f"m{index}": _baseline(index) for index in range(30)}
    for family, expected_feature_family in (
        ("M1_QIMEN", "QIMEN"),
        ("M2_MEIHUA", "MEIHUA"),
        ("M3_QIMEN_MEIHUA", "QIMEN_MEIHUA"),
    ):
        bundle = fit_model_family(
            rows,
            baselines,
            model_family=family,
            min_matches=20,
            l2_penalty=20.0,
        )
        assert bundle.residual_fit.feature_family == expected_feature_family
        assert bundle.residual_fit.converged_home
        assert bundle.residual_fit.converged_away
        forecast = predict_model_family(
            rows[-1],
            baselines[rows[-1].record.match_id],
            model_family=family,
            fit_bundle=bundle,
        )
        assert len(forecast.artifact_sources) == 2
        assert sum(cell[2] for cell in forecast.score_grid) == pytest.approx(1.0)


def test_dixon_coles_score_grid_is_supported_consistently():
    forecast = predict_model_family(
        _row(0),
        _baseline(0, score_model="DIXON_COLES"),
        model_family="M0_FOOTBALL",
    )
    assert sum(cell[2] for cell in forecast.score_grid) == pytest.approx(1.0)


def test_fit_uses_train_rows_only():
    rows = [_row(index) for index in range(25)] + [_row(100, role="VALIDATION")]
    baselines = {row.record.match_id: _baseline(int(row.record.match_id.removeprefix("m"))) for row in rows}
    bundle = fit_model_family(
        rows,
        baselines,
        model_family="M1_QIMEN",
        min_matches=20,
    )
    assert bundle.residual_fit.matches == 25


def test_model_family_guards_prevent_cross_wiring():
    rows = [_row(index) for index in range(25)]
    baselines = {f"m{index}": _baseline(index) for index in range(25)}
    qimen_fit = fit_model_family(rows, baselines, model_family="M1_QIMEN", min_matches=20)
    with pytest.raises(ValueError, match="fit bundle"):
        predict_model_family(
            rows[0],
            baselines["m0"],
            model_family="M2_MEIHUA",
            fit_bundle=qimen_fit,
        )
    with pytest.raises(ValueError, match="不可夾帶"):
        predict_model_family(
            rows[0],
            baselines["m0"],
            model_family="M0_FOOTBALL",
            fit_bundle=qimen_fit,
        )


def test_runner_forecast_is_compatible_with_common_evaluator():
    row = _row(0)
    forecast = predict_model_family(row, _baseline(0), model_family="M0_FOOTBALL")
    record = SimpleNamespace(
        match_id="m0",
        actual_home_goals=1,
        actual_away_goals=0,
        validate=lambda: [],
    )
    evaluation = evaluate_forecast(record, forecast)
    assert evaluation.match_id == "m0"
    assert evaluation.result_log_loss > 0
