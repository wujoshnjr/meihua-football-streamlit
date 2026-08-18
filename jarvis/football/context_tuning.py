from __future__ import annotations

from dataclasses import asdict, dataclass
from math import isfinite
from typing import Iterable, Mapping, Sequence

from jarvis.provenance import sha256_payload
from jarvis.research.dataset import MultiSignalDatasetRow
from jarvis.research.experiment import evaluate_forecast
from jarvis.research.residual import (
    ResidualLambdaFit,
    apply_residual_lambda_adjustment,
    fit_residual_lambda_adjustment,
)
from jarvis.research.runner import BaselineLambdaSnapshot, predict_model_family

from .context import (
    FOOTBALL_CONTEXT_FAMILY,
    FOOTBALL_CONTEXT_VERSION,
    FixtureContextSnapshot,
    build_context_residual_observation,
    fixture_context_numeric_features,
)


FOOTBALL_CONTEXT_TUNING_VERSION = "jarvis-football-context-validation-tuning-v0.1.0"


@dataclass(frozen=True)
class ContextDatasetRow:
    """One registered multisignal row bound to its prematch fixture context."""

    dataset_row: MultiSignalDatasetRow
    context_snapshot: FixtureContextSnapshot
    fingerprint_sha256: str

    @property
    def record(self):
        return self.dataset_row.record


@dataclass(frozen=True)
class ContextFitBundle:
    residual_fit: ResidualLambdaFit
    shrinkage_alpha: float = 1.0

    def __post_init__(self) -> None:
        if not isfinite(self.shrinkage_alpha) or not 0 <= self.shrinkage_alpha <= 1:
            raise ValueError("shrinkage_alpha 必須為 0 至 1 的有限數")
        if self.residual_fit.feature_family != FOOTBALL_CONTEXT_FAMILY:
            raise ValueError("context fit 的 feature_family 無效")
        if self.residual_fit.feature_schema_version != FOOTBALL_CONTEXT_VERSION:
            raise ValueError("context fit 的 feature schema 已過期")

    @property
    def artifact_source(self) -> str:
        return self.residual_fit.artifact_source


@dataclass(frozen=True)
class ContextTuningCandidate:
    l2_penalty: float
    shrinkage_alpha: float
    validation_matches: int
    mean_result_log_loss: float
    mean_brier_score: float
    mean_ranked_probability_score: float
    mean_exact_score_nll: float
    residual_artifact_source: str


@dataclass(frozen=True)
class ContextTuningResult:
    schema_version: str
    selected_l2_penalty: float
    selected_shrinkage_alpha: float
    selected_validation_log_loss: float
    selected_validation_brier: float
    validation_match_ids: tuple[str, ...]
    candidates: tuple[ContextTuningCandidate, ...]
    fit_bundle: ContextFitBundle
    artifact_sha256: str

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["fit_bundle"]["residual_fit"]["training_started_at"] = (
            self.fit_bundle.residual_fit.training_started_at.isoformat()
        )
        payload["fit_bundle"]["residual_fit"]["training_ended_at"] = (
            self.fit_bundle.residual_fit.training_ended_at.isoformat()
        )
        return payload


def bind_context_snapshot(
    row: MultiSignalDatasetRow,
    snapshot: FixtureContextSnapshot,
) -> ContextDatasetRow:
    """Bind context to one immutable match/cutoff without reading the result label."""

    if snapshot.schema_version != FOOTBALL_CONTEXT_VERSION:
        raise ValueError("fixture context schema 與目前版本不一致")
    if snapshot.cutoff_at != row.record.cutoff:
        raise ValueError("fixture context cutoff 與 dataset row cutoff 不一致")
    if snapshot.cutoff_at >= row.record.event_at:
        raise ValueError("fixture context cutoff 必須早於 event_at")
    core = {
        "dataset_row_fingerprint": row.fingerprint_sha256,
        "match_id": row.record.match_id,
        "event_at": row.record.event_at.isoformat(),
        "cutoff": row.record.cutoff.isoformat(),
        "context_fingerprint": snapshot.fingerprint_sha256,
        "context_schema": snapshot.schema_version,
        "home_team_id": snapshot.home_team_id,
        "away_team_id": snapshot.away_team_id,
    }
    return ContextDatasetRow(
        dataset_row=row,
        context_snapshot=snapshot,
        fingerprint_sha256=sha256_payload(core),
    )


def _baseline_for(
    row: ContextDatasetRow,
    baselines: Mapping[str, BaselineLambdaSnapshot],
) -> BaselineLambdaSnapshot:
    baseline = baselines.get(row.record.match_id)
    if baseline is None:
        raise ValueError(f"缺少 {row.record.match_id} 的 Football baseline lambda")
    errors = baseline.validate()
    if errors:
        raise ValueError("；".join(errors))
    if baseline.match_id != row.record.match_id:
        raise ValueError("baseline 與 context row 的 match_id 不一致")
    return baseline


def fit_context_challenger(
    rows: Iterable[ContextDatasetRow],
    baselines: Mapping[str, BaselineLambdaSnapshot],
    *,
    l2_penalty: float = 10.0,
    max_iter: int = 100,
    tolerance: float = 1e-7,
    min_matches: int = 200,
) -> ContextFitBundle:
    """Fit fixture-context coefficients on TRAIN only using the shared residual engine."""

    train_rows = tuple(
        sorted(
            (row for row in rows if row.record.dataset_role == "TRAIN"),
            key=lambda row: (row.record.event_at, row.record.match_id),
        )
    )
    if not train_rows:
        raise ValueError("沒有 TRAIN context rows 可擬合")
    observations = []
    for row in train_rows:
        baseline = _baseline_for(row, baselines)
        observations.append(
            build_context_residual_observation(
                row.context_snapshot,
                match_id=row.record.match_id,
                event_at=row.record.event_at,
                baseline_home_lambda=baseline.home_lambda,
                baseline_away_lambda=baseline.away_lambda,
                actual_home_goals=row.record.actual_home_goals,
                actual_away_goals=row.record.actual_away_goals,
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
    return ContextFitBundle(residual_fit=fit)


def apply_context_challenger(
    row: ContextDatasetRow,
    baseline: BaselineLambdaSnapshot,
    fit_bundle: ContextFitBundle,
) -> BaselineLambdaSnapshot:
    """Apply a frozen context residual and return a runner-compatible Football baseline."""

    errors = baseline.validate()
    if errors:
        raise ValueError("；".join(errors))
    if baseline.match_id != row.record.match_id:
        raise ValueError("baseline 與 context row 的 match_id 不一致")
    home_lambda, away_lambda = apply_residual_lambda_adjustment(
        baseline.home_lambda,
        baseline.away_lambda,
        fixture_context_numeric_features(row.context_snapshot),
        fit_bundle.residual_fit,
        feature_family=FOOTBALL_CONTEXT_FAMILY,
        feature_schema_version=FOOTBALL_CONTEXT_VERSION,
        shrinkage_alpha=fit_bundle.shrinkage_alpha,
    )
    source_fingerprint = sha256_payload(
        {
            "baseline_artifact_source": baseline.artifact_source,
            "context_row": row.fingerprint_sha256,
            "context_fit": fit_bundle.artifact_source,
            "shrinkage_alpha": fit_bundle.shrinkage_alpha,
            "home_lambda": home_lambda,
            "away_lambda": away_lambda,
        }
    )
    return BaselineLambdaSnapshot(
        match_id=baseline.match_id,
        home_lambda=home_lambda,
        away_lambda=away_lambda,
        artifact_source=f"football-context:{source_fingerprint}",
        score_model=baseline.score_model,
        dixon_coles_rho=baseline.dixon_coles_rho,
        max_goals=baseline.max_goals,
    )


def _validate_grid(l2_grid: Sequence[float], alpha_grid: Sequence[float]) -> None:
    if not l2_grid or any(not isfinite(value) or value <= 0 for value in l2_grid):
        raise ValueError("l2_grid 必須包含有限正數")
    if not alpha_grid or any(not isfinite(value) or not 0 <= value <= 1 for value in alpha_grid):
        raise ValueError("alpha_grid 必須全部介於 0 與 1")
    if not any(abs(value) <= 1e-15 for value in alpha_grid):
        raise ValueError("alpha_grid 必須包含 0，讓原 Football baseline 成為合法 fallback")
    if len(set(l2_grid)) != len(l2_grid) or len(set(alpha_grid)) != len(alpha_grid):
        raise ValueError("tuning grid 不可含重複值")


def tune_context_challenger(
    rows: Iterable[ContextDatasetRow],
    baselines: Mapping[str, BaselineLambdaSnapshot],
    *,
    l2_grid: Sequence[float] = (3.0, 10.0, 30.0, 100.0),
    alpha_grid: Sequence[float] = (0.0, 0.25, 0.5, 0.75, 1.0),
    min_train_matches: int = 200,
    max_iter: int = 100,
    tolerance: float = 1e-7,
) -> ContextTuningResult:
    """Select context L2 and shrinkage on VALIDATION only.

    TRAIN estimates coefficients. VALIDATION selects regularization and alpha.
    CALIBRATION and TEST_UNTOUCHED are ignored, so neither can influence context
    feature selection. ``alpha=0`` exactly recovers the registered Football
    lambdas and is mandatory in every candidate grid.
    """

    _validate_grid(l2_grid, alpha_grid)
    all_rows = tuple(rows)
    validation_rows = tuple(
        sorted(
            (row for row in all_rows if row.record.dataset_role == "VALIDATION"),
            key=lambda row: (row.record.event_at, row.record.match_id),
        )
    )
    if not validation_rows:
        raise ValueError("沒有 VALIDATION context rows 可選擇 hyperparameters")
    validation_ids = tuple(row.record.match_id for row in validation_rows)
    if len(set(validation_ids)) != len(validation_ids):
        raise ValueError("VALIDATION context rows 含重複 match_id")

    candidate_rows: list[tuple[ContextTuningCandidate, ContextFitBundle]] = []
    for l2_penalty in l2_grid:
        fitted = fit_context_challenger(
            all_rows,
            baselines,
            l2_penalty=float(l2_penalty),
            max_iter=max_iter,
            tolerance=tolerance,
            min_matches=min_train_matches,
        )
        for alpha in alpha_grid:
            bundle = ContextFitBundle(
                residual_fit=fitted.residual_fit,
                shrinkage_alpha=float(alpha),
            )
            evaluations = []
            for row in validation_rows:
                baseline = _baseline_for(row, baselines)
                adjusted = apply_context_challenger(row, baseline, bundle)
                forecast = predict_model_family(
                    row.dataset_row,
                    adjusted,
                    model_family="M0_FOOTBALL",
                )
                evaluations.append(evaluate_forecast(row.record, forecast))
            count = len(evaluations)
            candidate = ContextTuningCandidate(
                l2_penalty=float(l2_penalty),
                shrinkage_alpha=float(alpha),
                validation_matches=count,
                mean_result_log_loss=sum(item.result_log_loss for item in evaluations) / count,
                mean_brier_score=sum(item.brier_score for item in evaluations) / count,
                mean_ranked_probability_score=(
                    sum(item.ranked_probability_score for item in evaluations) / count
                ),
                mean_exact_score_nll=sum(item.exact_score_nll for item in evaluations) / count,
                residual_artifact_source=fitted.artifact_source,
            )
            candidate_rows.append((candidate, bundle))

    selected_candidate, selected_bundle = min(
        candidate_rows,
        key=lambda item: (
            item[0].mean_result_log_loss,
            item[0].mean_brier_score,
            item[0].shrinkage_alpha,
            -item[0].l2_penalty,
        ),
    )
    candidates = tuple(item[0] for item in candidate_rows)
    core = {
        "schema_version": FOOTBALL_CONTEXT_TUNING_VERSION,
        "context_schema_version": FOOTBALL_CONTEXT_VERSION,
        "validation_match_ids": validation_ids,
        "candidates": [asdict(candidate) for candidate in candidates],
        "selected_l2_penalty": selected_candidate.l2_penalty,
        "selected_shrinkage_alpha": selected_candidate.shrinkage_alpha,
        "selected_residual_artifact": selected_candidate.residual_artifact_source,
    }
    return ContextTuningResult(
        schema_version=FOOTBALL_CONTEXT_TUNING_VERSION,
        selected_l2_penalty=selected_candidate.l2_penalty,
        selected_shrinkage_alpha=selected_candidate.shrinkage_alpha,
        selected_validation_log_loss=selected_candidate.mean_result_log_loss,
        selected_validation_brier=selected_candidate.mean_brier_score,
        validation_match_ids=validation_ids,
        candidates=candidates,
        fit_bundle=selected_bundle,
        artifact_sha256=sha256_payload(core),
    )
