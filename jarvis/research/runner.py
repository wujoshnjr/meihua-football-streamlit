from __future__ import annotations

from dataclasses import dataclass
from math import exp, isfinite
from typing import Iterable, Literal, Mapping

from jarvis.provenance import sha256_payload
from qimen.training import dixon_coles_tau

from .dataset import MultiSignalDatasetRow
from .experiment import ModelFamily, ModelForecast
from .residual import (
    ResidualLambdaFit,
    ResidualLambdaObservation,
    apply_residual_lambda_adjustment,
    fit_residual_lambda_adjustment,
)


MULTISIGNAL_RUNNER_VERSION = "jarvis-m0-m3-runner-v0.2.0"
ScoreModel = Literal["INDEPENDENT_POISSON", "DIXON_COLES"]


@dataclass(frozen=True)
class BaselineLambdaSnapshot:
    """Registered football-only scoring intensities for one historical match."""

    match_id: str
    home_lambda: float
    away_lambda: float
    artifact_source: str
    score_model: ScoreModel = "INDEPENDENT_POISSON"
    dixon_coles_rho: float = 0.0
    max_goals: int = 10

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.match_id.strip():
            errors.append("baseline match_id 不可空白")
        for label, value in (("home_lambda", self.home_lambda), ("away_lambda", self.away_lambda)):
            if not isfinite(value) or value <= 0:
                errors.append(f"{self.match_id or '<unknown>'} {label} 必須為有限正數")
        if not self.artifact_source.strip():
            errors.append(f"{self.match_id or '<unknown>'} baseline artifact_source 不可空白")
        if self.score_model not in {"INDEPENDENT_POISSON", "DIXON_COLES"}:
            errors.append(f"{self.match_id or '<unknown>'} score_model 無效")
        if not isfinite(self.dixon_coles_rho) or not -0.25 <= self.dixon_coles_rho <= 0.25:
            errors.append(f"{self.match_id or '<unknown>'} Dixon-Coles rho 無效")
        if self.score_model == "INDEPENDENT_POISSON" and abs(self.dixon_coles_rho) > 1e-15:
            errors.append(f"{self.match_id or '<unknown>'} Independent Poisson 不可夾帶 rho")
        if isinstance(self.max_goals, bool) or not isinstance(self.max_goals, int) or not 5 <= self.max_goals <= 15:
            errors.append(f"{self.match_id or '<unknown>'} max_goals 必須介於 5 與 15")
        return errors


@dataclass(frozen=True)
class MultiSignalFitBundle:
    model_family: ModelFamily
    residual_fit: ResidualLambdaFit
    shrinkage_alpha: float = 1.0

    def __post_init__(self) -> None:
        if not isfinite(self.shrinkage_alpha) or not 0 <= self.shrinkage_alpha <= 1:
            raise ValueError("shrinkage_alpha 必須為 0 至 1 的有限數")

    @property
    def artifact_source(self) -> str:
        return self.residual_fit.artifact_source



def _poisson_probabilities(rate: float, max_goals: int) -> list[float]:
    probabilities = [exp(-rate)]
    for goals in range(1, max_goals + 1):
        probabilities.append(probabilities[-1] * rate / goals)
    return probabilities



def _score_grid(
    home_lambda: float,
    away_lambda: float,
    *,
    score_model: ScoreModel,
    dixon_coles_rho: float,
    max_goals: int,
) -> tuple[tuple[int, int, float], ...]:
    home_probs = _poisson_probabilities(home_lambda, max_goals)
    away_probs = _poisson_probabilities(away_lambda, max_goals)
    raw: list[tuple[int, int, float]] = []
    for home_goals, home_probability in enumerate(home_probs):
        for away_goals, away_probability in enumerate(away_probs):
            tau = 1.0
            if score_model == "DIXON_COLES":
                tau = dixon_coles_tau(
                    home_goals,
                    away_goals,
                    home_lambda,
                    away_lambda,
                    dixon_coles_rho,
                )
                if tau <= 0:
                    raise ValueError("Dixon-Coles rho 使比分矩陣校正係數不為正")
            raw.append((home_goals, away_goals, home_probability * away_probability * tau))
    mass = sum(cell[2] for cell in raw)
    if not isfinite(mass) or mass <= 0:
        raise ValueError("比分矩陣總質量無效")
    return tuple((home, away, probability / mass) for home, away, probability in raw)



def _signal_features(row: MultiSignalDatasetRow, model_family: ModelFamily) -> tuple[str, str, dict[str, float]]:
    if model_family == "M1_QIMEN":
        return (
            "QIMEN",
            row.record.qimen_snapshot.schema_version,
            dict(row.qimen_numeric_features),
        )
    if model_family == "M2_MEIHUA":
        return (
            "MEIHUA",
            row.record.meihua_snapshot.schema_version,
            dict(row.meihua_numeric_features),
        )
    if model_family == "M3_QIMEN_MEIHUA":
        features = {
            **{f"qimen::{name}": value for name, value in row.qimen_numeric_features.items()},
            **{f"meihua::{name}": value for name, value in row.meihua_numeric_features.items()},
        }
        schema = (
            f"qimen={row.record.qimen_snapshot.schema_version};"
            f"meihua={row.record.meihua_snapshot.schema_version}"
        )
        return "QIMEN_MEIHUA", schema, features
    raise ValueError("只有 M1/M2/M3 需要 signal residual features")



def fit_model_family(
    rows: Iterable[MultiSignalDatasetRow],
    baselines: Mapping[str, BaselineLambdaSnapshot],
    *,
    model_family: ModelFamily,
    l2_penalty: float = 10.0,
    max_iter: int = 100,
    tolerance: float = 1e-7,
    min_matches: int = 200,
) -> MultiSignalFitBundle:
    """Fit one M1/M2/M3 residual artifact using TRAIN rows only."""

    if model_family == "M0_FOOTBALL":
        raise ValueError("M0 Football 不需要 residual fit")
    train_rows = sorted(
        (row for row in rows if row.record.dataset_role == "TRAIN"),
        key=lambda row: (row.record.event_at, row.record.match_id),
    )
    if not train_rows:
        raise ValueError("沒有 TRAIN rows 可擬合 residual")
    observations: list[ResidualLambdaObservation] = []
    for row in train_rows:
        baseline = baselines.get(row.record.match_id)
        if baseline is None:
            raise ValueError(f"缺少 {row.record.match_id} 的 Football baseline lambda")
        baseline_errors = baseline.validate()
        if baseline_errors:
            raise ValueError("；".join(baseline_errors))
        if baseline.match_id != row.record.match_id:
            raise ValueError("baseline 與 dataset row 的 match_id 不一致")
        family, schema, features = _signal_features(row, model_family)
        payload_hash = sha256_payload(
            {
                "dataset_row": row.fingerprint_sha256,
                "baseline": {
                    "match_id": baseline.match_id,
                    "home_lambda": baseline.home_lambda,
                    "away_lambda": baseline.away_lambda,
                    "artifact_source": baseline.artifact_source,
                },
                "model_family": model_family,
                "features": dict(sorted(features.items())),
            }
        )
        observations.append(
            ResidualLambdaObservation(
                match_id=row.record.match_id,
                event_at=row.record.event_at,
                baseline_home_lambda=baseline.home_lambda,
                baseline_away_lambda=baseline.away_lambda,
                actual_home_goals=row.record.actual_home_goals,
                actual_away_goals=row.record.actual_away_goals,
                features=features,
                feature_family=family,
                feature_schema_version=schema,
                payload_sha256=payload_hash,
                dataset_role="TRAIN",
            )
        )
    fit = fit_residual_lambda_adjustment(
        observations,
        l2_penalty=l2_penalty,
        max_iter=max_iter,
        tolerance=tolerance,
        min_matches=min_matches,
    )
    return MultiSignalFitBundle(model_family=model_family, residual_fit=fit)



def predict_model_family(
    row: MultiSignalDatasetRow,
    baseline: BaselineLambdaSnapshot,
    *,
    model_family: ModelFamily,
    fit_bundle: MultiSignalFitBundle | None = None,
) -> ModelForecast:
    """Predict one M0/M1/M2/M3 row using one registered Football baseline."""

    errors = baseline.validate()
    if errors:
        raise ValueError("；".join(errors))
    if baseline.match_id != row.record.match_id:
        raise ValueError("baseline 與 dataset row 的 match_id 不一致")

    home_lambda = baseline.home_lambda
    away_lambda = baseline.away_lambda
    artifacts = [baseline.artifact_source]
    if model_family != "M0_FOOTBALL":
        if fit_bundle is None:
            raise ValueError(f"{model_family} 必須提供 residual fit")
        if fit_bundle.model_family != model_family:
            raise ValueError("fit bundle 與 requested model_family 不一致")
        family, schema, features = _signal_features(row, model_family)
        home_lambda, away_lambda = apply_residual_lambda_adjustment(
            home_lambda,
            away_lambda,
            features,
            fit_bundle.residual_fit,
            feature_family=family,
            feature_schema_version=schema,
            shrinkage_alpha=fit_bundle.shrinkage_alpha,
        )
        artifacts.append(fit_bundle.artifact_source)
    elif fit_bundle is not None:
        raise ValueError("M0 Football 不可夾帶 residual fit")

    grid = _score_grid(
        home_lambda,
        away_lambda,
        score_model=baseline.score_model,
        dixon_coles_rho=baseline.dixon_coles_rho,
        max_goals=baseline.max_goals,
    )
    home_probability = sum(probability for home, away, probability in grid if home > away)
    draw_probability = sum(probability for home, away, probability in grid if home == away)
    away_probability = sum(probability for home, away, probability in grid if home < away)
    model_version = (
        f"{MULTISIGNAL_RUNNER_VERSION}:{model_family}:{baseline.score_model}:"
        f"alpha={fit_bundle.shrinkage_alpha if fit_bundle else 0.0:.6f}"
    )
    return ModelForecast(
        match_id=row.record.match_id,
        model_family=model_family,
        model_version=model_version,
        home_win_probability=home_probability,
        draw_probability=draw_probability,
        away_win_probability=away_probability,
        expected_home_goals=home_lambda,
        expected_away_goals=away_lambda,
        score_grid=grid,
        artifact_sources=tuple(artifacts),
    )
