from __future__ import annotations

from dataclasses import dataclass, replace
from math import isfinite
from typing import Iterable

from jarvis.provenance import sha256_payload
from qimen.training import (
    CalibrationObservation,
    TemperatureCalibrationFit,
    fit_temperature_scaler,
    temperature_scale_probabilities,
)

from .dataset import MultiSignalDatasetRow
from .experiment import ModelFamily, ModelForecast


RESEARCH_CALIBRATION_VERSION = "jarvis-research-calibration-v0.1.0"


def _actual_result(row: MultiSignalDatasetRow) -> str:
    if row.record.actual_home_goals > row.record.actual_away_goals:
        return "主勝"
    if row.record.actual_home_goals < row.record.actual_away_goals:
        return "客勝"
    return "和局"


def _model_spec_sha256(forecast: ModelForecast) -> str:
    return sha256_payload(
        {
            "calibration_wrapper": RESEARCH_CALIBRATION_VERSION,
            "model_family": forecast.model_family,
            "uncalibrated_model_version": forecast.model_version,
        }
    )


@dataclass(frozen=True)
class ResearchCalibrationBundle:
    """CALIBRATION-only 1X2 probability calibration for one registered model family.

    The score grid and expected goals remain untouched. Temperature scaling is an
    outcome-probability calibration layer only, so exact-score evaluation continues
    to score the underlying Poisson/Dixon-Coles model rather than a fabricated score
    distribution.
    """

    model_family: ModelFamily
    uncalibrated_model_version: str
    model_spec_sha256: str
    temperature_fit: TemperatureCalibrationFit
    applied_temperature: float

    def __post_init__(self) -> None:
        if not isfinite(self.applied_temperature) or self.applied_temperature <= 0:
            raise ValueError("applied_temperature 必須為有限正數")
        if self.model_spec_sha256 != self.temperature_fit.model_spec_sha256:
            raise ValueError("calibration bundle model_spec_sha256 與 fit 不一致")

    @property
    def artifact_source(self) -> str:
        return self.temperature_fit.calibration_source


def fit_research_calibration(
    rows: Iterable[MultiSignalDatasetRow],
    forecasts: Iterable[ModelForecast],
    *,
    model_family: ModelFamily,
    temperature_min: float = 0.25,
    temperature_max: float = 4.0,
    grid_steps: int = 1501,
    min_matches: int = 200,
) -> ResearchCalibrationBundle:
    """Fit temperature scaling using CALIBRATION labels only.

    TRAIN/VALIDATION/TEST_UNTOUCHED rows are ignored by construction. All supplied
    forecasts must belong to the same registered model family/version; this prevents
    one calibration artifact from silently mixing different residual or score-model
    specifications.
    """

    dataset_rows = list(rows)
    if not dataset_rows:
        raise ValueError("至少需要一筆 dataset row")
    row_by_match = {row.record.match_id: row for row in dataset_rows}
    if len(row_by_match) != len(dataset_rows):
        raise ValueError("dataset rows 含重複 match_id")

    supplied = list(forecasts)
    if not supplied:
        raise ValueError("至少需要一筆 forecast")
    if len({forecast.match_id for forecast in supplied}) != len(supplied):
        raise ValueError("forecasts 含重複 match_id")
    if any(forecast.model_family != model_family for forecast in supplied):
        raise ValueError("forecast model_family 與 requested model_family 不一致")
    versions = {forecast.model_version for forecast in supplied}
    if len(versions) != 1:
        raise ValueError("同一 calibration bundle 不可混用不同 model_version")
    uncalibrated_model_version = next(iter(versions))

    observations: list[CalibrationObservation] = []
    expected_model_hash: str | None = None
    for forecast in sorted(supplied, key=lambda item: item.match_id):
        row = row_by_match.get(forecast.match_id)
        if row is None:
            raise ValueError(f"缺少 {forecast.match_id} 的 dataset row")
        if row.record.dataset_role != "CALIBRATION":
            continue
        errors = forecast.validate()
        if errors:
            raise ValueError("；".join(errors))
        model_hash = _model_spec_sha256(forecast)
        if expected_model_hash is None:
            expected_model_hash = model_hash
        elif model_hash != expected_model_hash:
            raise ValueError("CALIBRATION forecasts 的 model spec 不一致")
        probabilities = (
            forecast.home_win_probability,
            forecast.draw_probability,
            forecast.away_win_probability,
        )
        payload_hash = sha256_payload(
            {
                "dataset_row": row.fingerprint_sha256,
                "forecast": {
                    "match_id": forecast.match_id,
                    "model_family": forecast.model_family,
                    "model_version": forecast.model_version,
                    "probabilities": probabilities,
                    "artifact_sources": forecast.artifact_sources,
                },
            }
        )
        observations.append(
            CalibrationObservation(
                match_id=forecast.match_id,
                event_at=row.record.event_at,
                probabilities=probabilities,
                actual_result=_actual_result(row),
                model_spec_sha256=model_hash,
                payload_sha256=payload_hash,
                dataset_role="CALIBRATION",
            )
        )
    if expected_model_hash is None:
        raise ValueError("沒有 CALIBRATION forecasts 可擬合 calibration")

    fit = fit_temperature_scaler(
        observations,
        temperature_min=temperature_min,
        temperature_max=temperature_max,
        grid_steps=grid_steps,
        min_matches=min_matches,
    )
    applied_temperature = fit.temperature if fit.post_log_loss < fit.pre_log_loss - 1e-12 else 1.0
    return ResearchCalibrationBundle(
        model_family=model_family,
        uncalibrated_model_version=uncalibrated_model_version,
        model_spec_sha256=expected_model_hash,
        temperature_fit=fit,
        applied_temperature=applied_temperature,
    )


def apply_research_calibration(
    forecast: ModelForecast,
    bundle: ResearchCalibrationBundle,
) -> ModelForecast:
    """Apply a registered 1X2 calibration artifact without changing score lambdas/grid."""

    if forecast.model_family != bundle.model_family:
        raise ValueError("forecast model_family 與 calibration bundle 不一致")
    if forecast.model_version != bundle.uncalibrated_model_version:
        raise ValueError("forecast model_version 與 calibration bundle 不一致")
    if _model_spec_sha256(forecast) != bundle.model_spec_sha256:
        raise ValueError("forecast model spec 與 calibration bundle 不一致")
    probabilities = temperature_scale_probabilities(
        (
            forecast.home_win_probability,
            forecast.draw_probability,
            forecast.away_win_probability,
        ),
        bundle.applied_temperature,
    )
    return replace(
        forecast,
        model_version=(
            f"{forecast.model_version}:cal={RESEARCH_CALIBRATION_VERSION}:"
            f"T={bundle.applied_temperature:.6f}"
        ),
        home_win_probability=probabilities[0],
        draw_probability=probabilities[1],
        away_win_probability=probabilities[2],
        artifact_sources=(*forecast.artifact_sources, bundle.artifact_source),
    )
