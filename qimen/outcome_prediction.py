from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from math import exp, isfinite
from typing import Any

from .football import FootballReading
from .models import QimenBoard
from .outcome_features import (
    QimenOutcomeFeatureSnapshot,
    build_qimen_outcome_feature_snapshot,
)
from .prediction import (
    PrematchModelInput,
    PredictionResult,
    ScoreProbability,
    build_prediction,
)
from .protocol import MatchInput
from .score_metrics import exact_score_log_loss, exact_score_probability
from .training import dixon_coles_tau
from .venue import VenueBaseline, resolve_venue_baseline


OUTCOME_RESEARCH_VERSION = "jarvis-outcome-research-v0.1.0"


@dataclass(frozen=True)
class OutcomeResearchPrediction:
    """Venue-aware research bundle that leaves Qimen in shadow mode.

    The existing JARVIS prediction engine remains the source of football-only
    lambdas and 1X2 probabilities. This wrapper makes venue context explicit,
    retains a deterministic full score grid, and records raw Qimen outcome
    features for later chronological ablation tests.
    """

    schema_version: str
    venue_baseline: VenueBaseline
    prediction: PredictionResult
    score_grid: tuple[ScoreProbability, ...]
    qimen_outcome_features: QimenOutcomeFeatureSnapshot

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _poisson_probabilities(rate: float, max_goals: int) -> list[float]:
    probabilities = [exp(-rate)]
    for goals in range(1, max_goals + 1):
        probabilities.append(probabilities[-1] * rate / goals)
    return probabilities


def reconstruct_score_grid(prediction: PredictionResult) -> tuple[ScoreProbability, ...]:
    """Reconstruct the normalized score grid implied by a locked prediction.

    This is deterministic from the stored lambdas and score-model parameters,
    allowing exact-score evaluation before PredictionResult itself is migrated
    to retain the entire grid natively.
    """

    max_goals = prediction.model_input.get("max_goals")
    rho = prediction.model_input.get("dixon_coles_rho")
    if isinstance(max_goals, bool) or not isinstance(max_goals, int) or max_goals < 0:
        raise ValueError("prediction.model_input 的 max_goals 無效")
    if isinstance(rho, bool) or not isinstance(rho, (int, float)) or not isfinite(float(rho)):
        raise ValueError("prediction.model_input 的 dixon_coles_rho 無效")

    home_lambda = prediction.expected_home_goals
    away_lambda = prediction.expected_away_goals
    home_goal_probs = _poisson_probabilities(home_lambda, max_goals)
    away_goal_probs = _poisson_probabilities(away_lambda, max_goals)

    raw: list[tuple[int, int, float]] = []
    for home_goals, home_probability in enumerate(home_goal_probs):
        for away_goals, away_probability in enumerate(away_goal_probs):
            tau = 1.0
            if prediction.score_model == "DIXON_COLES":
                tau = dixon_coles_tau(
                    home_goals,
                    away_goals,
                    home_lambda,
                    away_lambda,
                    float(rho),
                )
                if tau <= 0:
                    raise ValueError("Dixon–Coles rho 使比分矩陣校正係數不為正")
            raw.append((home_goals, away_goals, home_probability * away_probability * tau))

    mass = sum(probability for _, _, probability in raw)
    if not isfinite(mass) or mass <= 0:
        raise ValueError("重建比分矩陣總質量無效")
    return tuple(
        ScoreProbability(home_goals, away_goals, probability / mass)
        for home_goals, away_goals, probability in raw
    )


def build_outcome_research_prediction(
    model_input: PrematchModelInput,
    board: QimenBoard,
    reading: FootballReading,
    match: MatchInput,
    *,
    venue_source: str,
    neutral_home_goals_per_match: float | None = None,
    neutral_away_goals_per_match: float | None = None,
) -> OutcomeResearchPrediction:
    """Build a venue-aware football forecast plus shadow Qimen research fields."""

    errors = match.validate()
    if errors:
        raise ValueError("；".join(errors))

    venue_baseline = resolve_venue_baseline(
        venue_mode=match.venue_mode,
        league_home_goals_per_match=model_input.league_home_goals_per_match,
        league_away_goals_per_match=model_input.league_away_goals_per_match,
        neutral_home_goals_per_match=neutral_home_goals_per_match,
        neutral_away_goals_per_match=neutral_away_goals_per_match,
        source=venue_source,
    )
    venue_adjusted_input = replace(
        model_input,
        league_home_goals_per_match=venue_baseline.home_goals_per_match,
        league_away_goals_per_match=venue_baseline.away_goals_per_match,
    )
    prediction = build_prediction(
        venue_adjusted_input,
        board,
        reading,
        match=match,
    )
    return OutcomeResearchPrediction(
        schema_version=OUTCOME_RESEARCH_VERSION,
        venue_baseline=venue_baseline,
        prediction=prediction,
        score_grid=reconstruct_score_grid(prediction),
        qimen_outcome_features=build_qimen_outcome_feature_snapshot(board, reading),
    )


def evaluate_exact_score(
    result: OutcomeResearchPrediction,
    actual_home_goals: int,
    actual_away_goals: int,
) -> dict[str, Any]:
    """Evaluate the complete score distribution without altering 1X2 calibration."""

    probability = exact_score_probability(
        result.score_grid,
        actual_home_goals,
        actual_away_goals,
    )
    return {
        "actual_score": (actual_home_goals, actual_away_goals),
        "exact_score_probability": probability,
        "exact_score_log_loss": exact_score_log_loss(
            result.score_grid,
            actual_home_goals,
            actual_away_goals,
        ),
        "score_grid_cells": len(result.score_grid),
        "venue_mode": result.venue_baseline.venue_mode,
        "qimen_mode": result.prediction.qimen_mode,
        "note": "精確比分以完整 raw score grid 評分；奇門仍為 SHADOW_ONLY。",
    }
