from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import exp, isfinite, log
from typing import Iterable

import numpy as np

DYNAMIC_STRENGTH_VERSION = "jarvis-opponent-adjusted-strength-v0.3.0"


@dataclass(frozen=True)
class DynamicStrengthObservation:
    """One historical match with an explicit venue/competition scoring baseline."""

    match_id: str
    event_at: datetime
    available_at: datetime
    home_team_id: str
    away_team_id: str
    home_goals: int
    away_goals: int
    baseline_home_goals_per_match: float
    baseline_away_goals_per_match: float
    source_payload_sha256: str
    home_xg: float | None = None
    away_xg: float | None = None

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.match_id.strip():
            errors.append("match_id 不可為空")
        if self.event_at.tzinfo is None or self.available_at.tzinfo is None:
            errors.append(f"{self.match_id} 的 event_at/available_at 必須含時區")
        elif self.available_at < self.event_at:
            errors.append(f"{self.match_id} 的 available_at 不可早於 event_at")
        if not self.home_team_id.strip() or not self.away_team_id.strip():
            errors.append(f"{self.match_id} 的隊伍 ID 不可空白")
        if self.home_team_id == self.away_team_id:
            errors.append(f"{self.match_id} 的主客隊不可相同")
        for label, value in (("home_goals", self.home_goals), ("away_goals", self.away_goals)):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                errors.append(f"{self.match_id} 的 {label} 必須為非負整數")
        for label, value in (
            ("baseline_home_goals_per_match", self.baseline_home_goals_per_match),
            ("baseline_away_goals_per_match", self.baseline_away_goals_per_match),
        ):
            if not isfinite(value) or value <= 0:
                errors.append(f"{self.match_id} 的 {label} 必須為有限正數")
        if (self.home_xg is None) != (self.away_xg is None):
            errors.append(f"{self.match_id} 的 home_xg/away_xg 必須同時存在或同時缺失")
        for label, value in (("home_xg", self.home_xg), ("away_xg", self.away_xg)):
            if value is not None and (not isfinite(value) or value < 0):
                errors.append(f"{self.match_id} 的 {label} 必須為有限非負數")
        if len(self.source_payload_sha256) != 64 or any(
            character not in "0123456789abcdef" for character in self.source_payload_sha256
        ):
            errors.append(f"{self.match_id} 的 source_payload_sha256 無效")
        return errors


@dataclass(frozen=True)
class TeamStrength:
    team_id: str
    attack_log_effect: float
    defence_weakness_log_effect: float
    effective_matches: float

    @property
    def attack_multiplier(self) -> float:
        return exp(self.attack_log_effect)

    @property
    def defence_weakness_multiplier(self) -> float:
        return exp(self.defence_weakness_log_effect)


@dataclass(frozen=True)
class DynamicStrengthFit:
    schema_version: str
    cutoff_at: datetime
    half_life_days: float
    l2_penalty: float
    matches: int
    teams: tuple[TeamStrength, ...]
    converged: bool
    iterations: int
    selected_match_ids: tuple[str, ...]
    identifiability_constraint: str = "SUM_TO_ZERO_ATTACK_AND_DEFENCE"
    xg_weight: float = 0.0
    target_definition: str = "GOALS_ONLY"

    def team(self, team_id: str) -> TeamStrength | None:
        return next((team for team in self.teams if team.team_id == team_id), None)


@dataclass(frozen=True)
class DynamicStrengthPrediction:
    home_lambda: float
    away_lambda: float
    home_attack_multiplier: float
    away_attack_multiplier: float
    home_defence_weakness_multiplier: float
    away_defence_weakness_multiplier: float
    cold_start_teams: tuple[str, ...]


def _sum_to_zero_contrast(team_count: int) -> np.ndarray:
    """Map K-1 free parameters to K effects whose arithmetic sum is exactly zero."""

    if team_count < 2:
        raise ValueError("動態攻防至少需要兩支隊伍")
    contrast = np.zeros((team_count, team_count - 1), dtype=float)
    contrast[:-1, :] = np.eye(team_count - 1, dtype=float)
    contrast[-1, :] = -1.0
    return contrast


def _fit_weighted_poisson(
    matrix: np.ndarray,
    offsets: np.ndarray,
    targets: np.ndarray,
    weights: np.ndarray,
    penalty_matrix: np.ndarray,
    *,
    l2_penalty: float,
    max_iter: int,
    tolerance: float,
) -> tuple[np.ndarray, bool, int]:
    """Fit a log-mean model using Poisson score equations.

    ``targets`` may be non-integer when the research-only xG blend is enabled.
    In that case this is a quasi-likelihood mean fit, not a claim that xG itself is
    a Poisson count. ``xg_weight=0`` preserves the original count likelihood.
    """

    coefficients = np.zeros(matrix.shape[1], dtype=float)
    for iteration in range(1, max_iter + 1):
        linear = np.clip(offsets + matrix @ coefficients, -12.0, 6.0)
        mean = np.exp(linear)
        residual = weights * (mean - targets)
        gradient = matrix.T @ residual + l2_penalty * (penalty_matrix @ coefficients)
        hessian = matrix.T @ (matrix * (weights * mean)[:, None]) + l2_penalty * penalty_matrix
        try:
            step = np.linalg.solve(hessian, gradient)
        except np.linalg.LinAlgError:
            step = np.linalg.pinv(hessian) @ gradient
        coefficients = coefficients - step
        if np.max(np.abs(step)) <= tolerance:
            return coefficients, True, iteration
    return coefficients, False, max_iter


def fit_dynamic_strength(
    observations: Iterable[DynamicStrengthObservation],
    *,
    cutoff_at: datetime,
    half_life_days: float = 180.0,
    l2_penalty: float = 8.0,
    xg_weight: float = 0.0,
    min_matches: int = 100,
    max_iter: int = 100,
    tolerance: float = 1e-7,
) -> DynamicStrengthFit:
    """Fit time-decayed opponent-adjusted attack and defence effects.

    For match i vs j, score intensities are modelled as
    ``baseline_home * exp(attack_i + defence_weakness_j)`` and
    ``baseline_away * exp(attack_j + defence_weakness_i)``. Attack and defence
    effects are each constrained to sum to zero across fitted teams.

    ``xg_weight`` is research-only. Targets become
    ``(1-xg_weight)*goals + xg_weight*xG`` so noisy finishing can be partially
    shrunk toward shot-quality production. It defaults to zero for exact backward
    compatibility and must be selected on VALIDATION rather than TEST_UNTOUCHED.
    """

    if cutoff_at.tzinfo is None:
        raise ValueError("cutoff_at 必須含時區")
    if not isfinite(half_life_days) or half_life_days <= 0:
        raise ValueError("half_life_days 必須為有限正數")
    if not isfinite(l2_penalty) or l2_penalty <= 0:
        raise ValueError("l2_penalty 必須為有限正數")
    if not isfinite(xg_weight) or not 0.0 <= xg_weight <= 1.0:
        raise ValueError("xg_weight 必須為 0 至 1 的有限數")
    if min_matches < 1:
        raise ValueError("min_matches 必須為正整數")
    if isinstance(max_iter, bool) or not isinstance(max_iter, int) or max_iter < 1:
        raise ValueError("max_iter 必須為正整數")
    if not isfinite(tolerance) or tolerance <= 0:
        raise ValueError("tolerance 必須為有限正數")

    all_rows = list(observations)
    errors = [error for row in all_rows for error in row.validate()]
    if errors:
        raise ValueError("；".join(errors))
    if len({row.match_id for row in all_rows}) != len(all_rows):
        raise ValueError("歷史資料含重複 match_id")
    rows = sorted(
        (row for row in all_rows if row.event_at < cutoff_at and row.available_at <= cutoff_at),
        key=lambda row: (row.event_at, row.match_id),
    )
    if len(rows) < min_matches:
        raise ValueError(f"動態攻防擬合至少需要 {min_matches} 場 cutoff 前資料")
    if xg_weight > 0 and any(row.home_xg is None or row.away_xg is None for row in rows):
        raise ValueError("xg_weight > 0 時所有 selected rows 都必須有 home_xg/away_xg")

    teams = tuple(sorted({row.home_team_id for row in rows} | {row.away_team_id for row in rows}))
    team_index = {team_id: index for index, team_id in enumerate(teams)}
    team_count = len(teams)
    contrast = _sum_to_zero_contrast(team_count)
    effect_dimension = team_count - 1
    matrix = np.zeros((2 * len(rows), 2 * effect_dimension), dtype=float)
    offsets = np.zeros(2 * len(rows), dtype=float)
    targets = np.zeros(2 * len(rows), dtype=float)
    weights = np.zeros(2 * len(rows), dtype=float)
    effective_matches = {team_id: 0.0 for team_id in teams}

    for match_index, row in enumerate(rows):
        age_days = (cutoff_at - row.event_at).total_seconds() / 86400.0
        weight = 0.5 ** (age_days / half_life_days)
        home_index = team_index[row.home_team_id]
        away_index = team_index[row.away_team_id]
        home_score_row = 2 * match_index
        away_score_row = home_score_row + 1

        matrix[home_score_row, :effect_dimension] = contrast[home_index]
        matrix[home_score_row, effect_dimension:] = contrast[away_index]
        matrix[away_score_row, :effect_dimension] = contrast[away_index]
        matrix[away_score_row, effect_dimension:] = contrast[home_index]
        offsets[home_score_row] = log(row.baseline_home_goals_per_match)
        offsets[away_score_row] = log(row.baseline_away_goals_per_match)
        home_target = float(row.home_goals)
        away_target = float(row.away_goals)
        if xg_weight > 0:
            assert row.home_xg is not None and row.away_xg is not None
            home_target = (1.0 - xg_weight) * home_target + xg_weight * row.home_xg
            away_target = (1.0 - xg_weight) * away_target + xg_weight * row.away_xg
        targets[home_score_row] = home_target
        targets[away_score_row] = away_target
        weights[home_score_row] = weight
        weights[away_score_row] = weight
        effective_matches[row.home_team_id] += weight
        effective_matches[row.away_team_id] += weight

    effect_penalty = contrast.T @ contrast
    penalty_matrix = np.zeros((2 * effect_dimension, 2 * effect_dimension), dtype=float)
    penalty_matrix[:effect_dimension, :effect_dimension] = effect_penalty
    penalty_matrix[effect_dimension:, effect_dimension:] = effect_penalty
    coefficients, converged, iterations = _fit_weighted_poisson(
        matrix,
        offsets,
        targets,
        weights,
        penalty_matrix,
        l2_penalty=l2_penalty,
        max_iter=max_iter,
        tolerance=tolerance,
    )
    attack_effects = contrast @ coefficients[:effect_dimension]
    defence_effects = contrast @ coefficients[effect_dimension:]
    team_strengths = tuple(
        TeamStrength(
            team_id=team_id,
            attack_log_effect=float(attack_effects[index]),
            defence_weakness_log_effect=float(defence_effects[index]),
            effective_matches=effective_matches[team_id],
        )
        for index, team_id in enumerate(teams)
    )
    return DynamicStrengthFit(
        schema_version=DYNAMIC_STRENGTH_VERSION,
        cutoff_at=cutoff_at,
        half_life_days=half_life_days,
        l2_penalty=l2_penalty,
        matches=len(rows),
        teams=team_strengths,
        converged=converged,
        iterations=iterations,
        selected_match_ids=tuple(row.match_id for row in rows),
        xg_weight=xg_weight,
        target_definition="GOALS_ONLY" if xg_weight == 0 else "GOALS_XG_CONVEX_BLEND",
    )


def predict_dynamic_lambdas(
    fit: DynamicStrengthFit,
    *,
    home_team_id: str,
    away_team_id: str,
    baseline_home_goals_per_match: float,
    baseline_away_goals_per_match: float,
    lower_bound: float = 0.15,
    upper_bound: float = 4.5,
) -> DynamicStrengthPrediction:
    """Apply fitted opponent-adjusted strengths; unseen teams shrink to baseline."""

    if not fit.converged:
        raise ValueError("dynamic strength fit 尚未收斂")
    if fit.identifiability_constraint != "SUM_TO_ZERO_ATTACK_AND_DEFENCE":
        raise ValueError("dynamic strength fit 缺少已註冊的 identifiability constraint")
    for label, value in (
        ("baseline_home_goals_per_match", baseline_home_goals_per_match),
        ("baseline_away_goals_per_match", baseline_away_goals_per_match),
    ):
        if not isfinite(value) or value <= 0:
            raise ValueError(f"{label} 必須為有限正數")
    if not 0 < lower_bound < upper_bound:
        raise ValueError("lambda bounds 無效")

    home = fit.team(home_team_id)
    away = fit.team(away_team_id)
    cold_start = tuple(
        team_id
        for team_id, strength in ((home_team_id, home), (away_team_id, away))
        if strength is None
    )
    home_attack = home.attack_multiplier if home else 1.0
    away_attack = away.attack_multiplier if away else 1.0
    home_defence = home.defence_weakness_multiplier if home else 1.0
    away_defence = away.defence_weakness_multiplier if away else 1.0
    home_lambda = baseline_home_goals_per_match * home_attack * away_defence
    away_lambda = baseline_away_goals_per_match * away_attack * home_defence
    return DynamicStrengthPrediction(
        home_lambda=min(upper_bound, max(lower_bound, home_lambda)),
        away_lambda=min(upper_bound, max(lower_bound, away_lambda)),
        home_attack_multiplier=home_attack,
        away_attack_multiplier=away_attack,
        home_defence_weakness_multiplier=home_defence,
        away_defence_weakness_multiplier=away_defence,
        cold_start_teams=cold_start,
    )
