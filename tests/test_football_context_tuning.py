from datetime import datetime, timedelta
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

from jarvis.football.context import FOOTBALL_CONTEXT_VERSION, FixtureContextSnapshot
from jarvis.football.context_tuning import (
    ContextFitBundle,
    apply_context_challenger,
    bind_context_snapshot,
    fit_context_challenger,
    tune_context_challenger,
)
from jarvis.research.runner import BaselineLambdaSnapshot


TZ = ZoneInfo("UTC")


def _dataset_row(index: int, role: str):
    event_at = datetime(2025, 1, 1, 20, tzinfo=TZ) + timedelta(days=index * 3)
    cutoff = event_at - timedelta(hours=8)
    record = SimpleNamespace(
        match_id=f"ctx-{index}",
        event_at=event_at,
        cutoff=cutoff,
        dataset_role=role,
        actual_home_goals=(index * 3 + 1) % 4,
        actual_away_goals=(index * 5 + 2) % 3,
        validate=lambda: [],
    )
    return SimpleNamespace(
        record=record,
        fingerprint_sha256=f"{index + 1:064x}",
    )


def _snapshot(index: int, cutoff: datetime) -> FixtureContextSnapshot:
    home_rest = 52.0 + float((index * 17) % 100)
    away_rest = 61.0 + float((index * 29) % 110)
    home_7 = (index * 2) % 4
    away_7 = (index * 3 + 1) % 4
    home_14 = home_7 + 1 + (index % 3)
    away_14 = away_7 + 1 + ((index * 2) % 3)
    return FixtureContextSnapshot(
        schema_version=FOOTBALL_CONTEXT_VERSION,
        cutoff_at=cutoff,
        home_team_id=f"H{index % 7}",
        away_team_id=f"A{index % 9}",
        home_previous_match_at=cutoff - timedelta(hours=home_rest),
        away_previous_match_at=cutoff - timedelta(hours=away_rest),
        home_rest_hours=home_rest,
        away_rest_hours=away_rest,
        home_matches_last_7d=home_7,
        away_matches_last_7d=away_7,
        home_matches_last_14d=home_14,
        away_matches_last_14d=away_14,
        selected_match_ids=(f"history-{index}",),
        fingerprint_sha256=f"{index + 1000:064x}",
    )


def _baseline(index: int) -> BaselineLambdaSnapshot:
    return BaselineLambdaSnapshot(
        match_id=f"ctx-{index}",
        home_lambda=1.25 + 0.04 * (index % 5),
        away_lambda=0.95 + 0.03 * (index % 4),
        artifact_source="football-baseline:test",
        max_goals=8,
    )


def _dataset():
    roles = ["TRAIN"] * 30 + ["VALIDATION"] * 8 + ["CALIBRATION"] * 4 + ["TEST_UNTOUCHED"] * 4
    rows = []
    baselines = {}
    for index, role in enumerate(roles):
        dataset_row = _dataset_row(index, role)
        rows.append(bind_context_snapshot(dataset_row, _snapshot(index, dataset_row.record.cutoff)))
        baselines[dataset_row.record.match_id] = _baseline(index)
    return rows, baselines


def test_context_alpha_zero_recovers_registered_football_lambdas():
    rows, baselines = _dataset()
    fitted = fit_context_challenger(rows, baselines, min_matches=20)
    bundle = ContextFitBundle(residual_fit=fitted.residual_fit, shrinkage_alpha=0.0)
    row = next(item for item in rows if item.record.dataset_role == "VALIDATION")
    baseline = baselines[row.record.match_id]

    adjusted = apply_context_challenger(row, baseline, bundle)

    assert adjusted.home_lambda == pytest.approx(baseline.home_lambda)
    assert adjusted.away_lambda == pytest.approx(baseline.away_lambda)
    assert adjusted.artifact_source.startswith("football-context:")


def test_context_tuning_uses_validation_only_and_records_candidates():
    rows, baselines = _dataset()
    result = tune_context_challenger(
        rows,
        baselines,
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


def test_context_tuning_requires_zero_alpha_fallback():
    rows, baselines = _dataset()
    with pytest.raises(ValueError, match="必須包含 0"):
        tune_context_challenger(
            rows,
            baselines,
            l2_grid=(10.0,),
            alpha_grid=(0.5, 1.0),
            min_train_matches=20,
        )


def test_context_tuning_ignores_test_labels():
    rows, baselines = _dataset()
    first = tune_context_challenger(
        rows,
        baselines,
        l2_grid=(10.0,),
        alpha_grid=(0.0, 0.5, 1.0),
        min_train_matches=20,
    )
    for row in rows:
        if row.record.dataset_role == "TEST_UNTOUCHED":
            row.record.actual_home_goals = 99
            row.record.actual_away_goals = 0
    second = tune_context_challenger(
        rows,
        baselines,
        l2_grid=(10.0,),
        alpha_grid=(0.0, 0.5, 1.0),
        min_train_matches=20,
    )

    assert second.selected_shrinkage_alpha == first.selected_shrinkage_alpha
    assert second.selected_validation_log_loss == pytest.approx(first.selected_validation_log_loss)


def test_context_binding_rejects_mismatched_cutoff():
    row = _dataset_row(1, "TRAIN")
    snapshot = _snapshot(1, row.record.cutoff + timedelta(minutes=1))
    with pytest.raises(ValueError, match="cutoff 與 dataset row cutoff 不一致"):
        bind_context_snapshot(row, snapshot)
