from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from math import isfinite
from typing import Any, Iterable, Mapping

from jarvis.research.residual import (
    GENERIC_RESIDUAL_FIT_VERSION,
    ResidualLambdaFit,
    ResidualLambdaObservation,
    apply_residual_lambda_adjustment,
    fit_residual_lambda_adjustment,
)

from .integrity import sha256_payload
from .outcome_design import QIMEN_OUTCOME_DESIGN_VERSION, validate_numeric_feature_row


QIMEN_LAMBDA_FIT_VERSION = "jarvis-qimen-lambda-fit-v0.3.0"
QIMEN_FEATURE_FAMILY = "QIMEN"


@dataclass(frozen=True)
class QimenLambdaObservation:
    """One pre-match football baseline plus Qimen design row and observed goals."""

    match_id: str
    event_at: datetime
    baseline_home_lambda: float
    baseline_away_lambda: float
    actual_home_goals: int
    actual_away_goals: int
    features: dict[str, float]
    payload_sha256: str
    dataset_role: str = "TRAIN"

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.match_id.strip():
            errors.append("Qimen lambda observation 必須有 match_id")
        if self.event_at.tzinfo is None:
            errors.append(f"{self.match_id} 的 event_at 必須含時區")
        if self.dataset_role != "TRAIN":
            errors.append(f"{self.match_id} 不是 TRAIN，不可擬合 Qimen lambda")
        for label, value in (
            ("baseline_home_lambda", self.baseline_home_lambda),
            ("baseline_away_lambda", self.baseline_away_lambda),
        ):
            if not isfinite(value) or value <= 0:
                errors.append(f"{self.match_id} 的 {label} 必須為有限正數")
        for label, value in (
            ("actual_home_goals", self.actual_home_goals),
            ("actual_away_goals", self.actual_away_goals),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                errors.append(f"{self.match_id} 的 {label} 必須為非負整數")
        try:
            validate_numeric_feature_row(self.features)
        except ValueError as exc:
            errors.append(f"{self.match_id}: {exc}")
        if len(self.payload_sha256) != 64 or any(
            character not in "0123456789abcdef" for character in self.payload_sha256
        ):
            errors.append(f"{self.match_id} 的 payload_sha256 無效")
        return errors

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["event_at"] = self.event_at.isoformat()
        payload["features"] = dict(sorted(self.features.items()))
        return payload

    def to_generic(self) -> ResidualLambdaObservation:
        return ResidualLambdaObservation(
            match_id=self.match_id,
            event_at=self.event_at,
            baseline_home_lambda=self.baseline_home_lambda,
            baseline_away_lambda=self.baseline_away_lambda,
            actual_home_goals=self.actual_home_goals,
            actual_away_goals=self.actual_away_goals,
            features=dict(self.features),
            feature_family=QIMEN_FEATURE_FAMILY,
            feature_schema_version=QIMEN_OUTCOME_DESIGN_VERSION,
            payload_sha256=self.payload_sha256,
            dataset_role=self.dataset_role,
        )


@dataclass(frozen=True)
class QimenLambdaFit:
    schema_version: str
    feature_schema_version: str
    generic_artifact_sha256: str
    git_commit: str
    feature_names: tuple[str, ...]
    home_coefficients: tuple[float, ...]
    away_coefficients: tuple[float, ...]
    l2_penalty: float
    matches: int
    training_started_at: datetime
    training_ended_at: datetime
    converged_home: bool
    converged_away: bool
    iterations_home: int
    iterations_away: int
    training_data_sha256: str
    artifact_sha256: str

    @property
    def artifact_source(self) -> str:
        return f"qimen-lambda-fit:{self.artifact_sha256}"

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["training_started_at"] = self.training_started_at.isoformat()
        payload["training_ended_at"] = self.training_ended_at.isoformat()
        payload["artifact_source"] = self.artifact_source
        return payload

    def to_generic(self) -> ResidualLambdaFit:
        return ResidualLambdaFit(
            schema_version=GENERIC_RESIDUAL_FIT_VERSION,
            feature_family=QIMEN_FEATURE_FAMILY,
            feature_schema_version=self.feature_schema_version,
            feature_names=self.feature_names,
            home_coefficients=self.home_coefficients,
            away_coefficients=self.away_coefficients,
            l2_penalty=self.l2_penalty,
            matches=self.matches,
            converged_home=self.converged_home,
            converged_away=self.converged_away,
            iterations_home=self.iterations_home,
            iterations_away=self.iterations_away,
            training_started_at=self.training_started_at,
            training_ended_at=self.training_ended_at,
            git_commit=self.git_commit,
            training_data_sha256=self.training_data_sha256,
            artifact_sha256=self.generic_artifact_sha256,
        )


def fit_qimen_lambda_adjustment(
    observations: Iterable[QimenLambdaObservation],
    *,
    l2_penalty: float = 10.0,
    max_iter: int = 100,
    tolerance: float = 1e-7,
    min_matches: int = 200,
) -> QimenLambdaFit:
    """Compatibility wrapper over the shared JARVIS residual engine.

    Qimen keeps its public artifact type and source prefix so existing hybrid code
    remains stable, but optimization, hidden-intercept checks and provenance are
    delegated to the same generic engine used by other v8 signal families.
    """

    rows = sorted(observations, key=lambda row: (row.event_at, row.match_id))
    errors = [error for row in rows for error in row.validate()]
    if errors:
        raise ValueError("；".join(errors))
    if len({row.match_id.strip() for row in rows}) != len(rows):
        raise ValueError("Qimen lambda TRAIN 資料含重複 match_id")

    generic_fit = fit_residual_lambda_adjustment(
        (row.to_generic() for row in rows),
        l2_penalty=l2_penalty,
        max_iter=max_iter,
        tolerance=tolerance,
        min_matches=min_matches,
    )
    core = {
        "schema_version": QIMEN_LAMBDA_FIT_VERSION,
        "feature_schema_version": generic_fit.feature_schema_version,
        "generic_artifact_sha256": generic_fit.artifact_sha256,
        "git_commit": generic_fit.git_commit,
        "feature_names": generic_fit.feature_names,
        "home_coefficients": generic_fit.home_coefficients,
        "away_coefficients": generic_fit.away_coefficients,
        "l2_penalty": generic_fit.l2_penalty,
        "matches": generic_fit.matches,
        "training_started_at": generic_fit.training_started_at.isoformat(),
        "training_ended_at": generic_fit.training_ended_at.isoformat(),
        "converged_home": generic_fit.converged_home,
        "converged_away": generic_fit.converged_away,
        "iterations_home": generic_fit.iterations_home,
        "iterations_away": generic_fit.iterations_away,
        "training_data_sha256": generic_fit.training_data_sha256,
    }
    artifact_sha256 = sha256_payload(core)
    return QimenLambdaFit(
        schema_version=QIMEN_LAMBDA_FIT_VERSION,
        feature_schema_version=generic_fit.feature_schema_version,
        generic_artifact_sha256=generic_fit.artifact_sha256,
        git_commit=generic_fit.git_commit,
        feature_names=generic_fit.feature_names,
        home_coefficients=generic_fit.home_coefficients,
        away_coefficients=generic_fit.away_coefficients,
        l2_penalty=generic_fit.l2_penalty,
        matches=generic_fit.matches,
        training_started_at=generic_fit.training_started_at,
        training_ended_at=generic_fit.training_ended_at,
        converged_home=generic_fit.converged_home,
        converged_away=generic_fit.converged_away,
        iterations_home=generic_fit.iterations_home,
        iterations_away=generic_fit.iterations_away,
        training_data_sha256=generic_fit.training_data_sha256,
        artifact_sha256=artifact_sha256,
    )


def apply_qimen_lambda_adjustment(
    baseline_home_lambda: float,
    baseline_away_lambda: float,
    features: Mapping[str, float],
    fit: QimenLambdaFit,
    *,
    lower_bound: float = 0.15,
    upper_bound: float = 4.5,
) -> tuple[float, float]:
    """Apply a Qimen compatibility artifact through the shared residual engine."""

    validate_numeric_feature_row(features)
    if fit.feature_schema_version != QIMEN_OUTCOME_DESIGN_VERSION:
        raise ValueError("Qimen feature schema 與目前 outcome design 版本不一致")
    return apply_residual_lambda_adjustment(
        baseline_home_lambda,
        baseline_away_lambda,
        features,
        fit.to_generic(),
        feature_family=QIMEN_FEATURE_FAMILY,
        feature_schema_version=QIMEN_OUTCOME_DESIGN_VERSION,
        lower_bound=lower_bound,
        upper_bound=upper_bound,
    )
