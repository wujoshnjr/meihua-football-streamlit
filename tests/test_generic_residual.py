from datetime import datetime, timedelta, timezone

import pytest

from jarvis.research.residual import (
    ResidualLambdaObservation,
    apply_residual_lambda_adjustment,
    fit_residual_lambda_adjustment,
)


def _rows(family="MEIHUA", schema="schema-v1"):
    start = datetime(2020, 1, 1, tzinfo=timezone.utc)
    rows = []
    for index in range(240):
        flag = float(index % 2)
        rows.append(
            ResidualLambdaObservation(
                match_id=f"M{index}",
                event_at=start + timedelta(days=index),
                baseline_home_lambda=1.0,
                baseline_away_lambda=1.0,
                actual_home_goals=2 if flag else 1,
                actual_away_goals=1,
                features={"flag": flag},
                feature_family=family,
                feature_schema_version=schema,
                payload_sha256="a" * 64,
            )
        )
    return rows


def test_generic_residual_learns_positive_home_shift_without_intercept():
    fit = fit_residual_lambda_adjustment(_rows(), l2_penalty=1.0)
    assert fit.converged_home
    assert fit.home_coefficients[0] > 0
    adjusted_home, adjusted_away = apply_residual_lambda_adjustment(
        1.0,
        1.0,
        {"flag": 1.0},
        fit,
        feature_family="MEIHUA",
        feature_schema_version="schema-v1",
    )
    assert adjusted_home > 1.0
    assert adjusted_away == pytest.approx(1.0, abs=1e-7)


def test_generic_residual_rejects_mixed_feature_families():
    rows = _rows()
    rows[-1] = ResidualLambdaObservation(
        **{**rows[-1].__dict__, "feature_family": "QIMEN"}
    )
    with pytest.raises(ValueError, match="不可混用"):
        fit_residual_lambda_adjustment(rows)
