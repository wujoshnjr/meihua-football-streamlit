from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from math import exp, factorial, isfinite, log
from typing import Iterable, Literal

from jarvis.provenance import sha256_payload

from .strength import (
    DynamicStrengthObservation,
    fit_dynamic_strength,
    predict_dynamic_lambdas,
)

DYNAMIC_STRENGTH_TUNING_VERSION = "jarvis-dynamic-strength-tuning-v0.1.0"
DatasetRole = Literal["VALIDATION"]


@dataclass(frozen=True)
class DynamicStrengthValidationFixture:
    """One held-out fixture used only to choose dynamic-strength hyperparameters."""

    match_id: str
    event_at: datetime
    cutoff_at: datetime
    home_team_id: str
    away_team_id: str
    baseline_home_goals_per_match: float
    baseline_away_goals_per_match: float
    actual_home_goals: int
    actual_away_goals: int
    dataset_role: DatasetRole = "VALIDATION"

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.match_id.strip():
            errors.append("validation match_id 不可空白")
        if self.event_at.tzinfo is None or self.cutoff_at.tzinfo is None:
            errors.append(f"{self.match_id} 的 event_at/cutoff_at 必須含時區")
        elif self.cutoff_at >= self.event_at:
            errors.append(f"{self.match_id} 必須在開賽前 cutoff")
        if self.dataset_role != "VALIDATION":
            errors.append(f"{self.match_id} 不是 VALIDATION，不可用於超參數選擇")
        if not self.home_team_id.strip() or not self.away_team_id.strip():
            errors.append(f"{self.match_id} 的隊伍 ID 不可空白")
        if self.home_team_id == self.away_team_id:
            errors.append(f"{self.match_id} 的主客隊不可相同")
        for label, value in (
            ("baseline_home_goals_per_match", self.baseline_home_goals_per_match),
            ("baseline_away_goals_per_match", self.baseline_away_goals_per_match),
        ):
            if not isfinite(value) or value <= 0:
                errors.append(f"{self.match_id} 的 {label} 必須為有限正數")
        for label, value in (
            ("actual_home_goals", self.actual_home_goals),
            ("actual_away_goals", self.actual_away_goals),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                errors.append(f"{self.match_id} 的 {label} 必須為非負整數")
        return errors


@dataclass(frozen=True)
class DynamicStrengthCandidateResult:
    half_life_days: float
    l2_penalty: float
    xg_weight: float
    matches: int
    mean_log_loss: float
    mean_brier_score: float


@dataclass(frozen=True)
class DynamicStrengthTuningResult:
    schema_version: str
    selected_half_life_days: float
    selected_l2_penalty: float
    selected_xg_weight: float
    validation_matches: int
    candidates: tuple[DynamicStrengthCandidateResult, ...]
    validation_started_at: datetime
    validation_ended_at: datetime
    artifact_sha256: str

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["validation_started_at"] = self.validation_started_at.isoformat()
        payload["validation_ended_at"] = self.validation_ended_at.isoformat()
        return payload


def _poisson_probability(goals: int, mean: float) -> float:
    return exp(-mean) * mean**goals / factorial(goals)


def _one_x_two_probabilities(home_lambda: float, away_lambda: float, *, max_goals: int = 10) -> tuple[float, float, float]:
    home = draw = away = total = 0.0
    for home_goals in range(max_goals + 1):
        home_probability = _poisson_probability(home_goals, home_lambda)
        for away_goals in range(max_goals + 1):
            probability = home_probability * _poisson_probability(away_goals, away_lambda)
            total += probability
            if home_goals > away_goals:
                home += probability
            elif home_goals == away_goals:
                draw += probability
            else:
                away += probability
    if total <= 0:
        raise ValueError("Poisson score grid 機率總和無效")
    return home / total, draw / total, away / total


def _score_fixture(probabilities: tuple[float, float, float], fixture: DynamicStrengthValidationFixture) -> tuple[float, float]:
    if fixture.actual_home_goals > fixture.actual_away_goals:
        actual_index = 0
    elif fixture.actual_home_goals == fixture.actual_away_goals:
        actual_index = 1
    else:
        actual_index = 2
    log_loss = -log(max(probabilities[actual_index], 1e-15))
    brier = sum(
        (probability - (1.0 if index == actual_index else 0.0)) ** 2
        for index, probability in enumerate(probabilities)
    )
    return log_loss, brier


def tune_dynamic_strength(
    observations: Iterable[DynamicStrengthObservation],
    validation_fixtures: Iterable[DynamicStrengthValidationFixture],
    *,
    half_life_days_grid: Iterable[float] = (90.0, 180.0, 365.0),
    l2_penalty_grid: Iterable[float] = (2.0, 8.0, 20.0),
    xg_weight_grid: Iterable[float] = (0.0, 0.25, 0.5, 0.75, 1.0),
    min_matches: int = 100,
) -> DynamicStrengthTuningResult:
    """Select dynamic-football hyperparameters using rolling-origin VALIDATION only.

    Each validation fixture is predicted from a fresh fit whose cutoff is that
    fixture's registered pre-match cutoff. This prevents later validation matches
    from entering earlier fits. ``xg_weight_grid`` must contain zero so goals-only
    remains an explicit fallback if xG does not improve held-out forecasts.
    """

    rows = list(observations)
    fixtures = sorted(validation_fixtures, key=lambda row: (row.event_at, row.match_id))
    if not fixtures:
        raise ValueError("至少需要一場 VALIDATION fixture")
    errors = [error for fixture in fixtures for error in fixture.validate()]
    if errors:
        raise ValueError("；".join(errors))
    if len({fixture.match_id for fixture in fixtures}) != len(fixtures):
        raise ValueError("VALIDATION fixtures 含重複 match_id")

    half_lives = tuple(float(value) for value in half_life_days_grid)
    penalties = tuple(float(value) for value in l2_penalty_grid)
    xg_weights = tuple(float(value) for value in xg_weight_grid)
    if not half_lives or any(not isfinite(value) or value <= 0 for value in half_lives):
        raise ValueError("half_life_days_grid 必須全部為有限正數")
    if not penalties or any(not isfinite(value) or value <= 0 for value in penalties):
        raise ValueError("l2_penalty_grid 必須全部為有限正數")
    if not xg_weights or any(not isfinite(value) or not 0 <= value <= 1 for value in xg_weights):
        raise ValueError("xg_weight_grid 必須全部介於 0 與 1")
    if 0.0 not in xg_weights:
        raise ValueError("xg_weight_grid 必須包含 0，保留 goals-only fallback")

    candidate_results: list[DynamicStrengthCandidateResult] = []
    for half_life_days in sorted(set(half_lives)):
        for l2_penalty in sorted(set(penalties)):
            for xg_weight in sorted(set(xg_weights)):
                losses: list[float] = []
                briers: list[float] = []
                for fixture in fixtures:
                    fit = fit_dynamic_strength(
                        rows,
                        cutoff_at=fixture.cutoff_at,
                        half_life_days=half_life_days,
                        l2_penalty=l2_penalty,
                        xg_weight=xg_weight,
                        min_matches=min_matches,
                    )
                    prediction = predict_dynamic_lambdas(
                        fit,
                        home_team_id=fixture.home_team_id,
                        away_team_id=fixture.away_team_id,
                        baseline_home_goals_per_match=fixture.baseline_home_goals_per_match,
                        baseline_away_goals_per_match=fixture.baseline_away_goals_per_match,
                    )
                    probabilities = _one_x_two_probabilities(prediction.home_lambda, prediction.away_lambda)
                    log_loss, brier = _score_fixture(probabilities, fixture)
                    losses.append(log_loss)
                    briers.append(brier)
                candidate_results.append(
                    DynamicStrengthCandidateResult(
                        half_life_days=half_life_days,
                        l2_penalty=l2_penalty,
                        xg_weight=xg_weight,
                        matches=len(fixtures),
                        mean_log_loss=sum(losses) / len(losses),
                        mean_brier_score=sum(briers) / len(briers),
                    )
                )

    ordered = tuple(
        sorted(
            candidate_results,
            key=lambda candidate: (
                candidate.mean_log_loss,
                candidate.mean_brier_score,
                candidate.xg_weight,
                -candidate.l2_penalty,
                -candidate.half_life_days,
            ),
        )
    )
    selected = ordered[0]
    core = {
        "schema_version": DYNAMIC_STRENGTH_TUNING_VERSION,
        "selected_half_life_days": selected.half_life_days,
        "selected_l2_penalty": selected.l2_penalty,
        "selected_xg_weight": selected.xg_weight,
        "validation_matches": len(fixtures),
        "validation_started_at": fixtures[0].event_at.isoformat(),
        "validation_ended_at": fixtures[-1].event_at.isoformat(),
        "candidates": [asdict(candidate) for candidate in ordered],
        "validation_match_ids": [fixture.match_id for fixture in fixtures],
    }
    return DynamicStrengthTuningResult(
        schema_version=DYNAMIC_STRENGTH_TUNING_VERSION,
        selected_half_life_days=selected.half_life_days,
        selected_l2_penalty=selected.l2_penalty,
        selected_xg_weight=selected.xg_weight,
        validation_matches=len(fixtures),
        candidates=ordered,
        validation_started_at=fixtures[0].event_at,
        validation_ended_at=fixtures[-1].event_at,
        artifact_sha256=sha256_payload(core),
    )
