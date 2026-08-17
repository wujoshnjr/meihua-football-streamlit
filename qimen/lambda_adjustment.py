from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from math import exp, isfinite
from typing import Any, Iterable, Mapping

import numpy as np

from .integrity import sha256_payload
from .outcome_design import validate_numeric_feature_row
from .runtime import detect_git_commit


QIMEN_LAMBDA_FIT_VERSION = "jarvis-qimen-lambda-fit-v0.2.0"


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


@dataclass(frozen=True)
class QimenLambdaFit:
    schema_version: str
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


def _fit_poisson_offset(
    matrix: np.ndarray,
    baseline_lambda: np.ndarray,
    goals: np.ndarray,
    *,
    l2_penalty: float,
    max_iter: int,
    tolerance: float,
) -> tuple[np.ndarray, bool, int]:
    """Fit log(mu)=log(baseline)+X beta with L2-penalized Newton steps.

    There is intentionally no intercept: if all Qimen coefficients are zero, the
    challenger exactly reproduces the football-only baseline instead of gaining a
    free global recalibration term. The design matrix is also checked explicitly
    so complete one-hot groups cannot recreate a hidden intercept.
    """

    coefficients = np.zeros(matrix.shape[1], dtype=float)
    identity = np.eye(matrix.shape[1], dtype=float)

    for iteration in range(1, max_iter + 1):
        linear = np.log(baseline_lambda) + matrix @ coefficients
        linear = np.clip(linear, -12.0, 6.0)
        mean = np.exp(linear)
        gradient = matrix.T @ (mean - goals) + l2_penalty * coefficients
        hessian = matrix.T @ (matrix * mean[:, None]) + l2_penalty * identity
        try:
            step = np.linalg.solve(hessian, gradient)
        except np.linalg.LinAlgError:
            step = np.linalg.pinv(hessian) @ gradient
        next_coefficients = coefficients - step
        if np.max(np.abs(step)) <= tolerance:
            return next_coefficients, True, iteration
        coefficients = next_coefficients

    return coefficients, False, max_iter


def _contains_constant_direction(matrix: np.ndarray, *, tolerance: float = 1e-10) -> bool:
    target = np.ones(matrix.shape[0], dtype=float)
    coefficients, *_ = np.linalg.lstsq(matrix, target, rcond=None)
    return bool(np.max(np.abs(matrix @ coefficients - target)) <= tolerance)


def fit_qimen_lambda_adjustment(
    observations: Iterable[QimenLambdaObservation],
    *,
    l2_penalty: float = 10.0,
    max_iter: int = 100,
    tolerance: float = 1e-7,
    min_matches: int = 200,
) -> QimenLambdaFit:
    """Fit home/away Qimen lambda adjustments using TRAIN-only observations."""

    rows = sorted(observations, key=lambda row: (row.event_at, row.match_id))
    if len(rows) < min_matches:
        raise ValueError(f"Qimen lambda 擬合至少需要 {min_matches} 場 TRAIN 樣本")
    if not isfinite(l2_penalty) or l2_penalty <= 0:
        raise ValueError("l2_penalty 必須為有限正數")
    if isinstance(max_iter, bool) or not isinstance(max_iter, int) or max_iter < 1:
        raise ValueError("max_iter 必須為正整數")
    if not isfinite(tolerance) or tolerance <= 0:
        raise ValueError("tolerance 必須為有限正數")

    errors = [error for row in rows for error in row.validate()]
    if errors:
        raise ValueError("；".join(errors))
    if len({row.match_id.strip() for row in rows}) != len(rows):
        raise ValueError("Qimen lambda TRAIN 資料含重複 match_id")

    feature_names = tuple(sorted({name for row in rows for name in row.features}))
    matrix = np.asarray(
        [[float(row.features.get(name, 0.0)) for name in feature_names] for row in rows],
        dtype=float,
    )
    if _contains_constant_direction(matrix):
        raise ValueError("Qimen feature design 含常數方向，會形成 hidden intercept；請使用 reference/effect coding")

    home_baseline = np.asarray([row.baseline_home_lambda for row in rows], dtype=float)
    away_baseline = np.asarray([row.baseline_away_lambda for row in rows], dtype=float)
    home_goals = np.asarray([row.actual_home_goals for row in rows], dtype=float)
    away_goals = np.asarray([row.actual_away_goals for row in rows], dtype=float)

    home_beta, converged_home, iterations_home = _fit_poisson_offset(
        matrix,
        home_baseline,
        home_goals,
        l2_penalty=l2_penalty,
        max_iter=max_iter,
        tolerance=tolerance,
    )
    away_beta, converged_away, iterations_away = _fit_poisson_offset(
        matrix,
        away_baseline,
        away_goals,
        l2_penalty=l2_penalty,
        max_iter=max_iter,
        tolerance=tolerance,
    )

    training_data = [row.to_dict() for row in rows]
    core = {
        "schema_version": QIMEN_LAMBDA_FIT_VERSION,
        "git_commit": detect_git_commit(),
        "feature_names": feature_names,
        "home_coefficients": tuple(float(value) for value in home_beta),
        "away_coefficients": tuple(float(value) for value in away_beta),
        "l2_penalty": l2_penalty,
        "matches": len(rows),
        "training_started_at": rows[0].event_at.isoformat(),
        "training_ended_at": rows[-1].event_at.isoformat(),
        "converged_home": converged_home,
        "converged_away": converged_away,
        "iterations_home": iterations_home,
        "iterations_away": iterations_away,
        "training_data_sha256": sha256_payload(training_data),
    }
    artifact_sha256 = sha256_payload(core)
    return QimenLambdaFit(
        schema_version=QIMEN_LAMBDA_FIT_VERSION,
        git_commit=core["git_commit"],
        feature_names=feature_names,
        home_coefficients=core["home_coefficients"],
        away_coefficients=core["away_coefficients"],
        l2_penalty=l2_penalty,
        matches=len(rows),
        training_started_at=rows[0].event_at,
        training_ended_at=rows[-1].event_at,
        converged_home=converged_home,
        converged_away=converged_away,
        iterations_home=iterations_home,
        iterations_away=iterations_away,
        training_data_sha256=core["training_data_sha256"],
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
    """Apply a fitted artifact; missing reference-coded fields are zero."""

    if not fit.converged_home or not fit.converged_away:
        raise ValueError("Qimen lambda fit 尚未收斂，不可套用")
    if not isfinite(baseline_home_lambda) or baseline_home_lambda <= 0:
        raise ValueError("baseline_home_lambda 必須為有限正數")
    if not isfinite(baseline_away_lambda) or baseline_away_lambda <= 0:
        raise ValueError("baseline_away_lambda 必須為有限正數")
    if not 0 < lower_bound < upper_bound:
        raise ValueError("lambda bounds 無效")
    validate_numeric_feature_row(features)

    unknown = set(features) - set(fit.feature_names)
    if unknown:
        raise ValueError("Qimen feature schema 與 fit 不一致：" + "、".join(sorted(unknown)))
    vector = [float(features.get(name, 0.0)) for name in fit.feature_names]
    home_shift = sum(value * beta for value, beta in zip(vector, fit.home_coefficients))
    away_shift = sum(value * beta for value, beta in zip(vector, fit.away_coefficients))
    home = baseline_home_lambda * exp(home_shift)
    away = baseline_away_lambda * exp(away_shift)
    return (
        min(upper_bound, max(lower_bound, home)),
        min(upper_bound, max(lower_bound, away)),
    )
