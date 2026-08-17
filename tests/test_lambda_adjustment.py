from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from jarvis.research.residual import fit_residual_lambda_adjustment
from qimen.lambda_adjustment import (
    QIMEN_FEATURE_FAMILY,
    QimenLambdaObservation,
    apply_qimen_lambda_adjustment,
    fit_qimen_lambda_adjustment,
)
from qimen.outcome_design import QIMEN_OUTCOME_DESIGN_VERSION


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
    assert fit.feature_schema_version == QIMEN_OUTCOME_DESIGN_VERSION
    assert len(fit.generic_artifact_sha256) == 64
    assert fit.feature_names == ("boost",)
    assert fit.home_coefficients[0] > 0
    assert fit.away_coefficients[0] == pytest.approx(0.0, abs=1e-8)

    unchanged = apply_qimen_lambda_adjustment(1.2, 0.9, {"boost": 0.0}, fit)
    adjusted = apply_qimen_lambda_adjustment(1.2, 0.9, {"boost": 1.0}, fit)
    assert unchanged == pytest.approx((1.2, 0.9))
    assert adjusted[0] > unchanged[0]
    assert adjusted[1] == pytest.approx(unchanged[1], abs=1e-8)


def test_qimen_wrapper_matches_generic_optimizer():
    rows = _rows(60)
    qimen_fit = fit_qimen_lambda_adjustment(rows, l2_penalty=0.5, min_matches=20)
    generic_fit = fit_residual_lambda_adjustment(
        (row.to_generic() for row in rows),
        l2_penalty=0.5,
        min_matches=20,
    )

    assert generic_fit.feature_family == QIMEN_FEATURE_FAMILY
    assert qimen_fit.generic_artifact_sha256 == generic_fit.artifact_sha256
    assert qimen_fit.home_coefficients == pytest.approx(generic_fit.home_coefficients)
    assert qimen_fit.away_coefficients == pytest.approx(generic_fit.away_coefficients)


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


def test_fit_rejects_hidden_intercept_from_complete_one_hot():
    rows = _rows(20)
    rows = [
        QimenLambdaObservation(
            **{
                **row.__dict__,
                "features": {
                    "door::A": 1.0 if index % 2 == 0 else 0.0,
                    "door::B": 1.0 if index % 2 == 1 else 0.0,
                },
            }
        )
        for index, row in enumerate(rows)
    ]
    with pytest.raises(ValueError, match="hidden intercept"):
        fit_qimen_lambda_adjustment(rows, min_matches=20)
