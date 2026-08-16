from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from qimen.lambda_adjustment import (
    QimenLambdaObservation,
    apply_qimen_lambda_adjustment,
    fit_qimen_lambda_adjustment,
)


def _rows(count: int = 60):
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    rows = []
    for index in range(count):
        boost = float(index % 2)
        rows.append(
            QimenLambdaObservation(
                match_id=f"M-{index:03d}",
                event_at=start + timedelta(days=index),
                baseline_home_lambda=1.0,
                baseline_away_lambda=1.0,
                actual_home_goals=2 if boost else 1,
                actual_away_goals=1,
                features={"boost": boost},
                payload_sha256=f"{index:064x}"[-64:],
            )
        )
    return rows


def test_fit_learns_incremental_home_shift_without_free_intercept():
    fit = fit_qimen_lambda_adjustment(
        _rows(),
        l2_penalty=0.01,
        min_matches=20,
    )

    assert fit.converged_home
    assert fit.converged_away
    assert fit.feature_names == ("boost",)
    assert fit.home_coefficients[0] > 0
    assert fit.away_coefficients[0] == pytest.approx(0.0, abs=1e-8)

    unchanged = apply_qimen_lambda_adjustment(1.2, 0.9, {"boost": 0.0}, fit)
    adjusted = apply_qimen_lambda_adjustment(1.2, 0.9, {"boost": 1.0}, fit)
    assert unchanged == pytest.approx((1.2, 0.9))
    assert adjusted[0] > unchanged[0]
    assert adjusted[1] == pytest.approx(unchanged[1], abs=1e-8)


def test_fit_rejects_non_train_rows():
    rows = _rows(20)
    rows[0] = QimenLambdaObservation(
        **{**rows[0].__dict__, "dataset_role": "VALIDATION"}
    )
    with pytest.raises(ValueError, match="不是 TRAIN"):
        fit_qimen_lambda_adjustment(rows, min_matches=20)


def test_apply_rejects_unknown_feature_schema():
    fit = fit_qimen_lambda_adjustment(_rows(20), min_matches=20)
    with pytest.raises(ValueError, match="schema"):
        apply_qimen_lambda_adjustment(
            1.0,
            1.0,
            {"boost": 1.0, "unregistered": 1.0},
            fit,
        )
