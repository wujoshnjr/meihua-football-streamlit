from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from math import exp, isfinite
from typing import Any, Iterable, Mapping

import numpy as np

from jarvis.provenance import detect_git_commit, sha256_payload

GENERIC_RESIDUAL_FIT_VERSION = "jarvis-generic-lambda-residual-v0.2.0"


@dataclass(frozen=True)
class ResidualLambdaObservation:
    match_id: str
    event_at: datetime
    baseline_home_lambda: float
    baseline_away_lambda: float
    actual_home_goals: int
    actual_away_goals: int
    features: dict[str, float]
    feature_family: str
    feature_schema_version: str
    payload_sha256: str
    dataset_role: str = "TRAIN"

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.match_id.strip():
            errors.append("match_id 不可為空")
        if self.event_at.tzinfo is None:
            errors.append(f"{self.match_id} 的 event_at 必須含時區")
        if self.dataset_role != "TRAIN":
            errors.append(f"{self.match_id} 不是 TRAIN，不可擬合 residual")
        if not self.feature_family.strip() or not self.feature_schema_version.strip():
            errors.append(f"{self.match_id} 缺少 feature family/schema")
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
        for name, value in self.features.items():
            if not name.strip() or not isfinite(float(value)):
                errors.append(f"{self.match_id} 的 feature {name!r} 無效")
        if len(self.payload_sha256) != 64 or any(c not in "0123456789abcdef" for c in self.payload_sha256):
            errors.append(f"{self.match_id} 的 payload_sha256 無效")
        return errors

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["event_at"] = self.event_at.isoformat()
        payload["features"] = dict(sorted(self.features.items()))
        return payload


@dataclass(frozen=True)
class ResidualLambdaFit:
    schema_version: str
    feature_family: str
    feature_schema_version: str
    feature_names: tuple[str, ...]
    home_coefficients: tuple[float, ...]
    away_coefficients: tuple[float, ...]
    l2_penalty: float
    matches: int
    converged_home: bool
    converged_away: bool
    iterations_home: int
    iterations_away: int
    training_started_at: datetime
    training_ended_at: datetime
    git_commit: str
    training_data_sha256: str
    artifact_sha256: str

    @property
    def artifact_source(self) -> str:
        return f"residual-lambda-fit:{self.artifact_sha256}"

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
    coefficients = np.zeros(matrix.shape[1], dtype=float)
    identity = np.eye(matrix.shape[1], dtype=float)
    for iteration in range(1, max_iter + 1):
        linear = np.clip(np.log(baseline_lambda) + matrix @ coefficients, -12.0, 6.0)
        mean = np.exp(linear)
        gradient = matrix.T @ (mean - goals) + l2_penalty * coefficients
        hessian = matrix.T @ (matrix * mean[:, None]) + l2_penalty * identity
        try:
            step = np.linalg.solve(hessian, gradient)
        except np.linalg.LinAlgError:
            step = np.linalg.pinv(hessian) @ gradient
        coefficients = coefficients - step
        if np.max(np.abs(step)) <= tolerance:
            return coefficients, True, iteration
    return coefficients, False, max_iter


def _contains_constant_direction(matrix: np.ndarray, *, tolerance: float = 1e-10) -> bool:
    """Return whether the design span can reproduce an all-ones intercept vector."""

    target = np.ones(matrix.shape[0], dtype=float)
    coefficients, *_ = np.linalg.lstsq(matrix, target, rcond=None)
    reconstruction = matrix @ coefficients
    return bool(np.max(np.abs(reconstruction - target)) <= tolerance)


def fit_residual_lambda_adjustment(
    observations: Iterable[ResidualLambdaObservation],
    *,
    l2_penalty: float = 10.0,
    max_iter: int = 100,
    tolerance: float = 1e-7,
    min_matches: int = 200,
) -> ResidualLambdaFit:
    rows = sorted(observations, key=lambda row: (row.event_at, row.match_id))
    if len(rows) < min_matches:
        raise ValueError(f"residual 擬合至少需要 {min_matches} 場 TRAIN 樣本")
    if not isfinite(l2_penalty) or l2_penalty <= 0:
        raise ValueError("l2_penalty 必須為有限正數")
    if isinstance(max_iter, bool) or not isinstance(max_iter, int) or max_iter < 1:
        raise ValueError("max_iter 必須為正整數")
    if not isfinite(tolerance) or tolerance <= 0:
        raise ValueError("tolerance 必須為有限正數")

    errors = [error for row in rows for error in row.validate()]
    if errors:
        raise ValueError("；".join(errors))
    if len({row.match_id for row in rows}) != len(rows):
        raise ValueError("TRAIN 資料含重複 match_id")
    families = {(row.feature_family, row.feature_schema_version) for row in rows}
    if len(families) != 1:
        raise ValueError("同一 residual fit 不可混用 feature family/schema")

    feature_names = tuple(sorted({name for row in rows for name in row.features}))
    if not feature_names:
        raise ValueError("residual fit 至少需要一個 feature")
    matrix = np.asarray(
        [[float(row.features.get(name, 0.0)) for name in feature_names] for row in rows],
        dtype=float,
    )
    if _contains_constant_direction(matrix):
        raise ValueError("feature design 含常數方向，會形成 hidden intercept；請使用 reference/effect coding")

    home_baseline = np.asarray([row.baseline_home_lambda for row in rows], dtype=float)
    away_baseline = np.asarray([row.baseline_away_lambda for row in rows], dtype=float)
    home_goals = np.asarray([row.actual_home_goals for row in rows], dtype=float)
    away_goals = np.asarray([row.actual_away_goals for row in rows], dtype=float)
    home_beta, converged_home, iterations_home = _fit_poisson_offset(
        matrix, home_baseline, home_goals, l2_penalty=l2_penalty, max_iter=max_iter, tolerance=tolerance
    )
    away_beta, converged_away, iterations_away = _fit_poisson_offset(
        matrix, away_baseline, away_goals, l2_penalty=l2_penalty, max_iter=max_iter, tolerance=tolerance
    )
    family, schema = next(iter(families))
    training_data = [row.to_dict() for row in rows]
    core = {
        "schema_version": GENERIC_RESIDUAL_FIT_VERSION,
        "feature_family": family,
        "feature_schema_version": schema,
        "feature_names": feature_names,
        "home_coefficients": tuple(float(value) for value in home_beta),
        "away_coefficients": tuple(float(value) for value in away_beta),
        "l2_penalty": l2_penalty,
        "matches": len(rows),
        "converged_home": converged_home,
        "converged_away": converged_away,
        "iterations_home": iterations_home,
        "iterations_away": iterations_away,
        "training_started_at": rows[0].event_at.isoformat(),
        "training_ended_at": rows[-1].event_at.isoformat(),
        "git_commit": detect_git_commit(),
        "training_data_sha256": sha256_payload(training_data),
    }
    artifact_sha256 = sha256_payload(core)
    return ResidualLambdaFit(
        schema_version=GENERIC_RESIDUAL_FIT_VERSION,
        feature_family=family,
        feature_schema_version=schema,
        feature_names=feature_names,
        home_coefficients=core["home_coefficients"],
        away_coefficients=core["away_coefficients"],
        l2_penalty=l2_penalty,
        matches=len(rows),
        converged_home=converged_home,
        converged_away=converged_away,
        iterations_home=iterations_home,
        iterations_away=iterations_away,
        training_started_at=rows[0].event_at,
        training_ended_at=rows[-1].event_at,
        git_commit=core["git_commit"],
        training_data_sha256=core["training_data_sha256"],
        artifact_sha256=artifact_sha256,
    )


def apply_residual_lambda_adjustment(
    baseline_home_lambda: float,
    baseline_away_lambda: float,
    features: Mapping[str, float],
    fit: ResidualLambdaFit,
    *,
    feature_family: str,
    feature_schema_version: str,
    lower_bound: float = 0.15,
    upper_bound: float = 4.5,
) -> tuple[float, float]:
    if not fit.converged_home or not fit.converged_away:
        raise ValueError("residual fit 尚未收斂，不可套用")
    if (feature_family, feature_schema_version) != (fit.feature_family, fit.feature_schema_version):
        raise ValueError("feature family/schema 與 residual fit 不一致")
    for label, value in (
        ("baseline_home_lambda", baseline_home_lambda),
        ("baseline_away_lambda", baseline_away_lambda),
    ):
        if not isfinite(value) or value <= 0:
            raise ValueError(f"{label} 必須為有限正數")
    if not 0 < lower_bound < upper_bound:
        raise ValueError("lambda bounds 無效")
    for name, value in features.items():
        if not name.strip() or not isfinite(float(value)):
            raise ValueError(f"feature {name!r} 無效")
    unknown = set(features) - set(fit.feature_names)
    if unknown:
        raise ValueError("feature schema 與 residual fit 不一致：" + "、".join(sorted(unknown)))
    if len(fit.home_coefficients) != len(fit.feature_names) or len(fit.away_coefficients) != len(fit.feature_names):
        raise ValueError("residual fit coefficient schema 損壞")
    vector = [float(features.get(name, 0.0)) for name in fit.feature_names]
    home_shift = sum(value * beta for value, beta in zip(vector, fit.home_coefficients))
    away_shift = sum(value * beta for value, beta in zip(vector, fit.away_coefficients))
    return (
        min(upper_bound, max(lower_bound, baseline_home_lambda * exp(home_shift))),
        min(upper_bound, max(lower_bound, baseline_away_lambda * exp(away_shift))),
    )
