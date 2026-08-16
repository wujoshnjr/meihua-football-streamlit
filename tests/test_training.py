from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from qimen.training import (
    CalibrationObservation,
    ChronologicalSample,
    DixonColesObservation,
    build_chronological_split_manifest,
    fit_dixon_coles_rho,
    fit_temperature_scaler,
    temperature_scale_probabilities,
)


HASH = "a" * 64


def test_chronological_manifest_enforces_four_ordered_layers():
    zone = ZoneInfo("UTC")
    start = datetime(2020, 1, 1, tzinfo=zone)
    samples = [
        ChronologicalSample(
            f"M-{index}", start + timedelta(days=index),
            "League", f"W{index}", HASH,
        )
        for index in range(8)
    ]
    manifest = build_chronological_split_manifest(
        reversed(samples),
        experiment_id="EXP-001",
        train_end=start + timedelta(days=1),
        validation_end=start + timedelta(days=3),
        calibration_end=start + timedelta(days=5),
    )
    assert manifest.counts == {
        "TRAIN": 2,
        "VALIDATION": 2,
        "CALIBRATION": 2,
        "TEST_UNTOUCHED": 2,
    }
    assert [row["dataset_role"] for row in manifest.assignments] == [
        "TRAIN", "TRAIN", "VALIDATION", "VALIDATION",
        "CALIBRATION", "CALIBRATION", "TEST_UNTOUCHED", "TEST_UNTOUCHED",
    ]
    assert len(manifest.test_set_sha256) == 64
    assert manifest.fingerprint_sha256 == build_chronological_split_manifest(
        samples,
        experiment_id="EXP-001",
        train_end=start + timedelta(days=1),
        validation_end=start + timedelta(days=3),
        calibration_end=start + timedelta(days=5),
    ).fingerprint_sha256


def test_chronological_manifest_rejects_empty_or_reversed_layers():
    zone = ZoneInfo("UTC")
    start = datetime(2020, 1, 1, tzinfo=zone)
    samples = [ChronologicalSample("M-1", start, "League", "W1", HASH)]
    with pytest.raises(ValueError, match="嚴格依"):
        build_chronological_split_manifest(
            samples,
            experiment_id="EXP",
            train_end=start + timedelta(days=2),
            validation_end=start + timedelta(days=1),
            calibration_end=start + timedelta(days=3),
        )
    with pytest.raises(ValueError, match="空層"):
        build_chronological_split_manifest(
            samples,
            experiment_id="EXP",
            train_end=start,
            validation_end=start + timedelta(days=1),
            calibration_end=start + timedelta(days=2),
        )


def test_dixon_coles_rho_is_fitted_only_from_train_with_time_decay():
    zone = ZoneInfo("UTC")
    start = datetime(2020, 1, 1, tzinfo=zone)
    score_pattern = (
        [(0, 0)] * 60
        + [(1, 1)] * 60
        + [(0, 1)] * 10
        + [(1, 0)] * 10
        + [(2, 1)] * 60
    )
    rows = [
        DixonColesObservation(
            f"DC-{index}", start + timedelta(days=index), 1.0, 1.0,
            home_goals, away_goals, HASH,
        )
        for index, (home_goals, away_goals) in enumerate(score_pattern)
    ]
    fit = fit_dixon_coles_rho(rows, grid_steps=401)
    assert fit.rho < 0
    assert fit.matches == 200
    assert fit.low_score_matches == 140
    assert fit.profile_ci_lower <= fit.rho <= fit.profile_ci_upper
    assert fit.rho_source.startswith("dc-rho-fit:")
    assert len(fit.artifact_sha256) == 64

    invalid_role = list(rows)
    invalid_role[0] = DixonColesObservation(
        "DC-INVALID", start, 1.0, 1.0, 0, 0, HASH, dataset_role="VALIDATION",
    )
    with pytest.raises(ValueError, match="不是 TRAIN"):
        fit_dixon_coles_rho(invalid_role, grid_steps=101)


def test_temperature_scaler_uses_calibration_only_and_reduces_overconfidence():
    zone = ZoneInfo("UTC")
    start = datetime(2022, 1, 1, tzinfo=zone)
    labels = ("主勝", "和局", "客勝")
    rows: list[CalibrationObservation] = []
    for index in range(300):
        predicted_index = index % 3
        actual_index = predicted_index if index % 5 < 3 else (predicted_index + 1) % 3
        probabilities = tuple(
            0.90 if position == predicted_index else 0.05
            for position in range(3)
        )
        rows.append(CalibrationObservation(
            f"CAL-{index}", start + timedelta(days=index), probabilities,
            labels[actual_index], "b" * 64, HASH,
        ))

    fit = fit_temperature_scaler(rows, grid_steps=501)
    assert fit.temperature > 1.0
    assert fit.post_log_loss < fit.pre_log_loss
    assert fit.calibration_source.startswith("temperature-fit:")
    calibrated = temperature_scale_probabilities((0.8, 0.1, 0.1), fit.temperature)
    assert sum(calibrated) == pytest.approx(1.0)
    assert calibrated[0] < 0.8

    invalid_role = list(rows)
    invalid_role[0] = CalibrationObservation(
        "CAL-INVALID", start, (0.8, 0.1, 0.1), "主勝",
        "b" * 64, HASH, dataset_role="TEST_UNTOUCHED",
    )
    with pytest.raises(ValueError, match="不是 CALIBRATION"):
        fit_temperature_scaler(invalid_role, grid_steps=101)
