from datetime import datetime, timedelta
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

from jarvis.research.runner import (
    BaselineLambdaSnapshot,
    MultiSignalFitBundle,
    fit_model_family,
    predict_model_family,
)
from jarvis.research.tuning import tune_model_family


TZ = ZoneInfo("UTC")


def _row(index: int, role: str):
    event_at = datetime(2025, 1, 1, 20, tzinfo=TZ) + timedelta(days=index)
    record = SimpleNamespace(
        match_id=f"m{index}",
        event_at=event_at,
        dataset_role=role,
        actual_home_goals=1 + (index % 2),
        actual_away_goals=index % 2,
        qimen_snapshot=SimpleNamespace(schema_version="qimen-test-v1"),
        meihua_snapshot=SimpleNamespace(schema_version="meihua-test-v1"),
        validate=lambda: [],
    )
    return SimpleNamespace(
        record=record,
        fingerprint_sha256=f"{index:064x}"[-64:],
        qimen_numeric_features={"q_signal": float((index % 5) - 2)},
        meihua_numeric_features={"m_signal": float(((index * index + index) % 7) - 3)},
    )


def _baseline(index: int) -> BaselineLambdaSnapshot:
    return BaselineLambdaSnapshot(
        match_id=f"m{index}",
        home_lambda=1.3 + 0.01 * (index % 3),
        away_lambda=0.9 + 0.01 * (index % 4),
        artifact_source="football-baseline:test",
        max_goals=8,
    )


def _dataset():
    rows = []
    roles = ["TRAIN"] * 30 + ["VALIDATION"] * 8 + ["CALIBRATION"] * 4 + ["TEST_UNTOUCHED"] * 4
    for index, role in enumerate(roles):
        rows.append(_row(index, role))
    baselines = {row.record.match_id: _baseline(index) for index, row in enumerate(rows)}
    return rows, baselines


def test_alpha_zero_exactly_recovers_football_baseline():
    rows, baselines = _dataset()
    fitted = fit_model_family(
        rows,
        baselines,
        model_family="M1_QIMEN",
        min_matches=20,
    )
    zero_bundle = MultiSignalFitBundle(
        model_family="M1_QIMEN",
        residual_fit=fitted.residual_fit,
        shrinkage_alpha=0.0,
    )
    row = next(item for item in rows if item.record.dataset_role == "VALIDATION")
    baseline = baselines[row.record.match_id]
    forecast = predict_model_family(
        row,
        baseline,
        model_family="M1_QIMEN",
        fit_bundle=zero_bundle,
    )
    assert forecast.expected_home_goals == pytest.approx(baseline.home_lambda)
    assert forecast.expected_away_goals == pytest.approx(baseline.away_lambda)


def test_tuning_scores_only_validation_and_records_all_candidates():
    rows, baselines = _dataset()
    result = tune_model_family(
        rows,
        baselines,
        model_family="M1_QIMEN",
        l2_grid=(5.0, 20.0),
        alpha_grid=(0.0, 0.5, 1.0),
        min_train_matches=20,
    )
    expected_validation = tuple(
        row.record.match_id for row in rows if row.record.dataset_role == "VALIDATION"
    )
    assert result.validation_match_ids == expected_validation
    assert len(result.candidates) == 6
    assert result.selected_l2_penalty in {5.0, 20.0}
    assert result.selected_shrinkage_alpha in {0.0, 0.5, 1.0}
    assert result.fit_bundle.shrinkage_alpha == result.selected_shrinkage_alpha
    assert len(result.artifact_sha256) == 64


def test_tuning_requires_zero_alpha_fallback():
    rows, baselines = _dataset()
    with pytest.raises(ValueError, match="必須包含 0"):
        tune_model_family(
            rows,
            baselines,
            model_family="M2_MEIHUA",
            l2_grid=(10.0,),
            alpha_grid=(0.5, 1.0),
            min_train_matches=20,
        )


def test_tuning_ignores_test_labels_when_selecting_hyperparameters():
    rows, baselines = _dataset()
    first = tune_model_family(
        rows,
        baselines,
        model_family="M2_MEIHUA",
        l2_grid=(10.0,),
        alpha_grid=(0.0, 0.5, 1.0),
        min_train_matches=20,
    )
    for row in rows:
        if row.record.dataset_role == "TEST_UNTOUCHED":
            row.record.actual_home_goals = 99
            row.record.actual_away_goals = 0
    second = tune_model_family(
        rows,
        baselines,
        model_family="M2_MEIHUA",
        l2_grid=(10.0,),
        alpha_grid=(0.0, 0.5, 1.0),
        min_train_matches=20,
    )
    assert second.selected_shrinkage_alpha == first.selected_shrinkage_alpha
    assert second.selected_validation_log_loss == pytest.approx(first.selected_validation_log_loss)
