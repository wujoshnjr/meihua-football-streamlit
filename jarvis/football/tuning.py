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

DYNAMIC_STRENGTH_TUNING_VERSION = "jarvis-dynamic-strength-tuning-v0.2.0"
DatasetRole = Literal["VALIDATION"]
ScoreModel = Literal["INDEPENDENT_POISSON", "DIXON_COLES"]


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
    mean_exact_score_nll: float


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
    score_model: ScoreModel = "INDEPENDENT_POISSON"
    dixon_coles_rho: float = 0.0
    max_goals: int = 10

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["validation_started_at"] = self.validation_started_at.isoformat()
        payload["validation_ended_at"] = self.validation_ended_at.isoformat()
        return payload


@dataclass(frozen=True)
class _FixtureScore:
    probabilities: tuple[float, float, float]
    exact_score_probability: float


def _poisson_probability(goals: int, mean: float) -> float:
    return exp(-mean) * mean**goals / factorial(goals)


def _dixon_coles_tau(
    home_goals: int,
    away_goals: int,
    home_lambda: float,
    away_lambda: float,
    rho: float,
) -> float:
    if home_goals == 0 and away_goals == 0:
        return 1.0 - home_lambda * away_lambda * rho
    if home_goals == 0 and away_goals == 1:
        return 1.0 + home_lambda * rho
    if home_goals == 1 and away_goals == 0:
        return 1.0 + away_lambda * rho
    if home_goals == 1 and away_goals == 1:
        return 1.0 - rho
    return 1.0


def _score_distribution(
    home_lambda: float,
    away_lambda: float,
    fixture: DynamicStrengthValidationFixture,
    *,
    score_model: ScoreModel,
    dixon_coles_rho: float,
    max_goals: int,
) -> _FixtureScore:
    home = draw = away = total = 0.0
    actual_probability = 0.0
    for home_goals in range(max_goals + 1):
        home_probability = _poisson_probability(home_goals, home_lambda)
        for away_goals in range(max_goals + 1):
            probability = home_probability * _poisson_probability(away_goals, away_lambda)
            if score_model == "DIXON_COLES":
                tau = _dixon_coles_tau(
                    home_goals,
                    away_goals,
                    home_lambda,
                    away_lambda,
                    dixon_coles_rho,
                )
                if not isfinite(tau) or tau <= 0:
                    raise ValueError("Dixon–Coles rho 對 validation lambda 產生非正 tau")
                probability *= tau
            total += probability
            if home_goals > away_goals:
                home += probability
            elif home_goals == away_goals:
                draw += probability
            else:
                away += probability
            if (
                home_goals == fixture.actual_home_goals
                and away_goals == fixture.actual_away_goals
            ):
                actual_probability = probability
    if total <= 0 or not isfinite(total):
        raise ValueError("score grid 機率總和無效")
    return _FixtureScore(
        probabilities=(home / total, draw / total, away / total),
        exact_score_probability=actual_probability / total,
    )


def _score_fixture(
    score: _FixtureScore,
    fixture: DynamicStrengthValidationFixture,
) -> tuple[float, float, float]:
    if fixture.actual_home_goals > fixture.actual_away_goals:
        actual_index = 0
    elif fixture.actual_home_goals == fixture.actual_away_goals:
        actual_index = 1
    else:
        actual_index = 2
    log_loss = -log(max(score.probabilities[actual_index], 1e-15))
    brier = sum(
        (probability - (1.0 if index == actual_index else 0.0)) ** 2
        for index, probability in enumerate(score.probabilities)
    )
    exact_score_nll = -log(max(score.exact_score_probability, 1e-15))
    return log_loss, brier, exact_score_nll


def tune_dynamic_strength(
    observations: Iterable[DynamicStrengthObservation],
    validation_fixtures: Iterable[DynamicStrengthValidationFixture],
    *,
    half_life_days_grid: Iterable[float] = (90.0, 180.0, 365.0),
    l2_penalty_grid: Iterable[float] = (2.0, 8.0, 20.0),
    xg_weight_grid: Iterable[float] = (0.0, 0.25, 0.5, 0.75, 1.0),
    min_matches: int = 100,
    score_model: ScoreModel = "INDEPENDENT_POISSON",
    dixon_coles_rho: float = 0.0,
    max_goals: int = 10,
) -> DynamicStrengthTuningResult:
    """Select dynamic-football hyperparameters using rolling-origin VALIDATION only.

    Each validation fixture is predicted from a fresh fit whose cutoff is that
    fixture's registered pre-match cutoff. This prevents later validation matches
    from entering earlier fits. ``xg_weight_grid`` must contain zero so goals-only
    remains an explicit fallback if xG does not improve held-out forecasts.

    Candidate scoring uses the registered downstream score model. This prevents
    selecting attack/defence hyperparameters under independent Poisson and then
    evaluating the frozen challenger under a different Dixon–Coles distribution.
    Dixon–Coles ``rho`` is an already-frozen upstream TRAIN artifact value; this
    tuner does not re-estimate rho on VALIDATION.
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
    if score_model not in {"INDEPENDENT_POISSON", "DIXON_COLES"}:
        raise ValueError("score_model 必須為 INDEPENDENT_POISSON 或 DIXON_COLES")
    if not isfinite(dixon_coles_rho) or not -0.25 <= dixon_coles_rho <= 0.25:
        raise ValueError("dixon_coles_rho 必須為 -0.25 至 0.25 的有限數")
    if score_model == "INDEPENDENT_POISSON" and abs(dixon_coles_rho) > 1e-15:
        raise ValueError("INDEPENDENT_POISSON tuning 不可夾帶 Dixon–Coles rho")
    if isinstance(max_goals, bool) or not isinstance(max_goals, int) or not 5 <= max_goals <= 15:
        raise ValueError("max_goals 必須為 5 至 15 的整數")
    if any(
        fixture.actual_home_goals > max_goals or fixture.actual_away_goals > max_goals
        for fixture in fixtures
    ):
        raise ValueError("validation 實際比分超過 max_goals，exact-score NLL 無法正確計算")

    candidate_results: list[DynamicStrengthCandidateResult] = []
    for half_life_days in sorted(set(half_lives)):
        for l2_penalty in sorted(set(penalties)):
            for xg_weight in sorted(set(xg_weights)):
                losses: list[float] = []
                briers: list[float] = []
                exact_nlls: list[float] = []
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
                    score = _score_distribution(
                        prediction.home_lambda,
                        prediction.away_lambda,
                        fixture,
                        score_model=score_model,
                        dixon_coles_rho=dixon_coles_rho,
                        max_goals=max_goals,
                    )
                    log_loss, brier, exact_score_nll = _score_fixture(score, fixture)
                    losses.append(log_loss)
                    briers.append(brier)
                    exact_nlls.append(exact_score_nll)
                candidate_results.append(
                    DynamicStrengthCandidateResult(
                        half_life_days=half_life_days,
                        l2_penalty=l2_penalty,
                        xg_weight=xg_weight,
                        matches=len(fixtures),
                        mean_log_loss=sum(losses) / len(losses),
                        mean_brier_score=sum(briers) / len(briers),
                        mean_exact_score_nll=sum(exact_nlls) / len(exact_nlls),
                    )
                )

    ordered = tuple(
        sorted(
            candidate_results,
            key=lambda candidate: (
                candidate.mean_log_loss,
                candidate.mean_brier_score,
                candidate.mean_exact_score_nll,
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
        "score_model": score_model,
        "dixon_coles_rho": dixon_coles_rho,
        "max_goals": max_goals,
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
        score_model=score_model,
        dixon_coles_rho=dixon_coles_rho,
        max_goals=max_goals,
    )