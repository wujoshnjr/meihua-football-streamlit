from __future__ import annotations

from dataclasses import asdict, dataclass
from math import isfinite
from typing import Iterable, Mapping, Sequence

from jarvis.provenance import sha256_payload

from .dataset import MultiSignalDatasetRow
from .experiment import ModelFamily, evaluate_forecast
from .runner import (
    BaselineLambdaSnapshot,
    MultiSignalFitBundle,
    fit_model_family,
    predict_model_family,
)


RESIDUAL_TUNING_VERSION = "jarvis-residual-validation-tuning-v0.1.0"


@dataclass(frozen=True)
class TuningCandidate:
    l2_penalty: float
    shrinkage_alpha: float
    validation_matches: int
    mean_result_log_loss: float
    mean_brier_score: float
    mean_ranked_probability_score: float
    mean_exact_score_nll: float
    residual_artifact_source: str


@dataclass(frozen=True)
class ResidualTuningResult:
    schema_version: str
    model_family: ModelFamily
    selected_l2_penalty: float
    selected_shrinkage_alpha: float
    selected_validation_log_loss: float
    selected_validation_brier: float
    validation_match_ids: tuple[str, ...]
    candidates: tuple[TuningCandidate, ...]
    fit_bundle: MultiSignalFitBundle
    artifact_sha256: str

    def to_dict(self):
        payload = asdict(self)
        payload["fit_bundle"]["residual_fit"]["training_started_at"] = (
            self.fit_bundle.residual_fit.training_started_at.isoformat()
        )
        payload["fit_bundle"]["residual_fit"]["training_ended_at"] = (
            self.fit_bundle.residual_fit.training_ended_at.isoformat()
        )
        return payload



def _validate_grid(l2_grid: Sequence[float], alpha_grid: Sequence[float]) -> None:
    if not l2_grid:
        raise ValueError("l2_grid 不可空白")
    if not alpha_grid:
        raise ValueError("alpha_grid 不可空白")
    if any(not isfinite(value) or value <= 0 for value in l2_grid):
        raise ValueError("l2_grid 必須全部為有限正數")
    if any(not isfinite(value) or not 0 <= value <= 1 for value in alpha_grid):
        raise ValueError("alpha_grid 必須全部介於 0 與 1")
    if not any(abs(value) <= 1e-15 for value in alpha_grid):
        raise ValueError("alpha_grid 必須包含 0，讓 Football baseline 成為合法 fallback")
    if len(set(l2_grid)) != len(l2_grid) or len(set(alpha_grid)) != len(alpha_grid):
        raise ValueError("tuning grid 不可含重複值")



def tune_model_family(
    rows: Iterable[MultiSignalDatasetRow],
    baselines: Mapping[str, BaselineLambdaSnapshot],
    *,
    model_family: ModelFamily,
    l2_grid: Sequence[float] = (3.0, 10.0, 30.0, 100.0),
    alpha_grid: Sequence[float] = (0.0, 0.25, 0.5, 0.75, 1.0),
    min_train_matches: int = 200,
    max_iter: int = 100,
    tolerance: float = 1e-7,
) -> ResidualTuningResult:
    """Select residual regularization and global shrinkage on VALIDATION only.

    Coefficients are always learned on TRAIN through ``fit_model_family``. The
    function evaluates only immutable VALIDATION rows. CALIBRATION and
    TEST_UNTOUCHED rows are ignored, so neither can influence L2 or alpha.
    """

    if model_family == "M0_FOOTBALL":
        raise ValueError("M0 Football 不需要 residual tuning")
    _validate_grid(l2_grid, alpha_grid)
    all_rows = tuple(rows)
    validation_rows = tuple(
        sorted(
            (row for row in all_rows if row.record.dataset_role == "VALIDATION"),
            key=lambda row: (row.record.event_at, row.record.match_id),
        )
    )
    if not validation_rows:
        raise ValueError("沒有 VALIDATION rows 可選擇 residual hyperparameters")
    validation_ids = tuple(row.record.match_id for row in validation_rows)
    if len(set(validation_ids)) != len(validation_ids):
        raise ValueError("VALIDATION rows 含重複 match_id")

    candidate_rows: list[tuple[TuningCandidate, MultiSignalFitBundle]] = []
    for l2_penalty in l2_grid:
        fitted = fit_model_family(
            all_rows,
            baselines,
            model_family=model_family,
            l2_penalty=float(l2_penalty),
            max_iter=max_iter,
            tolerance=tolerance,
            min_matches=min_train_matches,
        )
        for alpha in alpha_grid:
            bundle = MultiSignalFitBundle(
                model_family=model_family,
                residual_fit=fitted.residual_fit,
                shrinkage_alpha=float(alpha),
            )
            evaluations = []
            for row in validation_rows:
                baseline = baselines.get(row.record.match_id)
                if baseline is None:
                    raise ValueError(f"缺少 {row.record.match_id} 的 VALIDATION Football baseline lambda")
                forecast = predict_model_family(
                    row,
                    baseline,
                    model_family=model_family,
                    fit_bundle=bundle,
                )
                evaluations.append(evaluate_forecast(row.record, forecast))
            count = len(evaluations)
            candidate = TuningCandidate(
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
        "schema_version": RESIDUAL_TUNING_VERSION,
        "model_family": model_family,
        "validation_match_ids": validation_ids,
        "candidates": [asdict(candidate) for candidate in candidates],
        "selected_l2_penalty": selected_candidate.l2_penalty,
        "selected_shrinkage_alpha": selected_candidate.shrinkage_alpha,
        "selected_residual_artifact": selected_candidate.residual_artifact_source,
    }
    return ResidualTuningResult(
        schema_version=RESIDUAL_TUNING_VERSION,
        model_family=model_family,
        selected_l2_penalty=selected_candidate.l2_penalty,
        selected_shrinkage_alpha=selected_candidate.shrinkage_alpha,
        selected_validation_log_loss=selected_candidate.mean_result_log_loss,
        selected_validation_brier=selected_candidate.mean_brier_score,
        validation_match_ids=validation_ids,
        candidates=candidates,
        fit_bundle=selected_bundle,
        artifact_sha256=sha256_payload(core),
    )
