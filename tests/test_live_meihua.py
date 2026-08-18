from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from jarvis.live_meihua import (
    LIVE_MEIHUA_ARTIFACT_VERSION,
    LiveMeihuaArtifact,
    build_live_meihua_forecast,
    load_deployed_live_meihua_artifact,
)
from jarvis.provenance import sha256_payload
from jarvis.research.residual import GENERIC_RESIDUAL_FIT_VERSION, ResidualLambdaFit
from meihua import MEIHUA_OUTCOME_DESIGN_VERSION, build_meihua_snapshot, meihua_outcome_numeric_features
from qimen.prediction import INDEPENDENT_POISSON_VERSION, PredictionResult, ScoreProbability


TZ = ZoneInfo("Asia/Taipei")
EVENT_AT = datetime(2026, 8, 20, 20, 0, tzinfo=TZ)


def _base_prediction() -> PredictionResult:
    return PredictionResult(
        model_version=INDEPENDENT_POISSON_VERSION,
        score_model="INDEPENDENT_POISSON",
        qimen_feature_version="fixture-qimen-v1",
        model_status="BASELINE_READY",
        calibration_status="UNCALIBRATED_V0",
        qimen_mode="SHADOW_ONLY",
        forecast_horizon="EARLY",
        lineup_status="UNAVAILABLE",
        calibration_source="",
        expected_home_goals=1.55,
        expected_away_goals=1.10,
        raw_home_win_probability=0.48,
        raw_draw_probability=0.27,
        raw_away_win_probability=0.25,
        home_win_probability=0.48,
        draw_probability=0.27,
        away_win_probability=0.25,
        predicted_result="主勝",
        decision_margin=0.21,
        top_scorelines=(
            ScoreProbability(1, 0, 0.18),
            ScoreProbability(1, 1, 0.16),
            ScoreProbability(2, 0, 0.14),
        ),
        score_grid_tail_mass=0.0,
        model_input={
            "max_goals": 10,
            "dixon_coles_rho": 0.0,
            "score_model": "INDEPENDENT_POISSON",
        },
        qimen_features={},
        provenance={},
        data_warnings=(),
        disclaimer="fixture",
    )


def _artifact(*, alpha: float = 0.5) -> LiveMeihuaArtifact:
    snapshot = build_meihua_snapshot(EVENT_AT, "Asia/Taipei")
    features = meihua_outcome_numeric_features(snapshot)
    feature_names = tuple(sorted(features))
    active_name = next(name for name, value in features.items() if value == 1.0)
    home_coefficients = tuple(0.20 if name == active_name else 0.0 for name in feature_names)
    away_coefficients = tuple(-0.10 if name == active_name else 0.0 for name in feature_names)
    started = EVENT_AT - timedelta(days=500)
    ended = EVENT_AT - timedelta(days=100)
    residual_core = {
        "schema_version": GENERIC_RESIDUAL_FIT_VERSION,
        "feature_family": "MEIHUA",
        "feature_schema_version": MEIHUA_OUTCOME_DESIGN_VERSION,
        "feature_names": feature_names,
        "home_coefficients": home_coefficients,
        "away_coefficients": away_coefficients,
        "l2_penalty": 10.0,
        "matches": 500,
        "converged_home": True,
        "converged_away": True,
        "iterations_home": 4,
        "iterations_away": 5,
        "training_started_at": started.isoformat(),
        "training_ended_at": ended.isoformat(),
        "git_commit": "1" * 40,
        "training_data_sha256": "a" * 64,
    }
    residual = ResidualLambdaFit(
        schema_version=GENERIC_RESIDUAL_FIT_VERSION,
        feature_family="MEIHUA",
        feature_schema_version=MEIHUA_OUTCOME_DESIGN_VERSION,
        feature_names=feature_names,
        home_coefficients=home_coefficients,
        away_coefficients=away_coefficients,
        l2_penalty=10.0,
        matches=500,
        converged_home=True,
        converged_away=True,
        iterations_home=4,
        iterations_away=5,
        training_started_at=started,
        training_ended_at=ended,
        git_commit="1" * 40,
        training_data_sha256="a" * 64,
        artifact_sha256=sha256_payload(residual_core),
    )
    artifact = LiveMeihuaArtifact(
        schema_version=LIVE_MEIHUA_ARTIFACT_VERSION,
        model_family="M2_MEIHUA",
        feature_family="MEIHUA",
        feature_schema_version=MEIHUA_OUTCOME_DESIGN_VERSION,
        baseline_model_version=INDEPENDENT_POISSON_VERSION,
        score_model="INDEPENDENT_POISSON",
        dixon_coles_rho=0.0,
        max_goals=10,
        residual_fit=residual,
        shrinkage_alpha=alpha,
        tuning_artifact_sha256="b" * 64,
        calibration_temperature=1.0,
        calibration_artifact_sha256="c" * 64,
        promotion_report_sha256="d" * 64,
        promotion_status="ELIGIBLE_FOR_HUMAN_REVIEW",
        approved_for_live=True,
        approved_at=EVENT_AT - timedelta(days=30),
        approved_by="fixture-reviewer",
        source_commit="2" * 40,
        artifact_sha256="0" * 64,
    )
    return replace(artifact, artifact_sha256=sha256_payload(artifact._core()))


def test_without_promoted_artifact_meihua_is_computed_but_probabilities_are_exact_baseline():
    base = _base_prediction()
    forecast = build_live_meihua_forecast(
        base,
        event_at=EVENT_AT,
        timezone_name="Asia/Taipei",
        artifact=None,
    )

    assert forecast.mode == "ADVISORY_ONLY_NO_PROMOTED_ARTIFACT"
    assert forecast.active_probability_adjustment is False
    assert forecast.home_win_probability == base.home_win_probability
    assert forecast.draw_probability == base.draw_probability
    assert forecast.away_win_probability == base.away_win_probability
    assert forecast.expected_home_goals == base.expected_home_goals
    assert forecast.expected_away_goals == base.expected_away_goals
    assert len(forecast.meihua_feature_sha256) == 64
    assert forecast.meihua_numeric_features


def test_valid_promoted_m2_artifact_changes_lambdas_and_rescores_probabilities():
    base = _base_prediction()
    artifact = _artifact(alpha=0.5)
    assert artifact.validate() == []

    forecast = build_live_meihua_forecast(
        base,
        event_at=EVENT_AT,
        timezone_name="Asia/Taipei",
        artifact=artifact,
    )

    assert forecast.mode == "ACTIVE_PROMOTED_M2_MEIHUA"
    assert forecast.active_probability_adjustment is True
    assert forecast.model_family == "M2_MEIHUA"
    assert forecast.expected_home_goals > base.expected_home_goals
    assert forecast.expected_away_goals < base.expected_away_goals
    assert abs(
        forecast.home_win_probability
        + forecast.draw_probability
        + forecast.away_win_probability
        - 1.0
    ) < 1e-12
    assert forecast.artifact_source == artifact.artifact_source
    assert len(forecast.forecast_sha256) == 64


def test_validation_selected_alpha_zero_is_exact_football_fallback():
    base = _base_prediction()
    artifact = _artifact(alpha=0.0)

    forecast = build_live_meihua_forecast(
        base,
        event_at=EVENT_AT,
        timezone_name="Asia/Taipei",
        artifact=artifact,
    )

    assert forecast.mode == "PROMOTED_M2_BASELINE_FALLBACK"
    assert forecast.active_probability_adjustment is False
    assert forecast.home_win_probability == base.home_win_probability
    assert forecast.expected_home_goals == base.expected_home_goals


def test_tampered_or_wrong_baseline_artifact_is_rejected():
    base = _base_prediction()
    artifact = _artifact()
    tampered = replace(artifact, artifact_sha256="f" * 64)

    with pytest.raises(ValueError, match="deployment artifact SHA-256"):
        build_live_meihua_forecast(
            base,
            event_at=EVENT_AT,
            timezone_name="Asia/Taipei",
            artifact=tampered,
        )

    wrong_baseline = replace(
        artifact,
        baseline_model_version="different-baseline-v1",
        artifact_sha256="0" * 64,
    )
    wrong_baseline = replace(
        wrong_baseline,
        artifact_sha256=sha256_payload(wrong_baseline._core()),
    )
    with pytest.raises(ValueError, match="Football baseline"):
        build_live_meihua_forecast(
            base,
            event_at=EVENT_AT,
            timezone_name="Asia/Taipei",
            artifact=wrong_baseline,
        )


def test_loader_returns_none_when_no_deployed_artifact(tmp_path):
    assert load_deployed_live_meihua_artifact(tmp_path / "missing.json") is None
