from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from math import log
from typing import Any

from .football import FootballReading
from .lambda_adjustment import QimenLambdaFit, apply_qimen_lambda_adjustment
from .models import QimenBoard
from .outcome_design import qimen_outcome_numeric_features
from .outcome_prediction import (
    OutcomeResearchPrediction,
    build_outcome_research_prediction,
    reconstruct_score_grid,
)
from .prediction import PrematchModelInput, ScoreProbability
from .protocol import MatchInput
from .score_metrics import exact_score_log_loss, exact_score_probability
from .training import temperature_scale_probabilities


QIMEN_HYBRID_VERSION = "jarvis-qimen-hybrid-challenger-v0.1.0"


@dataclass(frozen=True)
class QimenHybridPrediction:
    """Side-by-side football baseline and fitted-Qimen research challenger.

    This object is deliberately separate from ``PredictionResult`` so a fitted
    Qimen artifact cannot silently become the production model. Promotion must
    happen only through the registered chronological model-comparison process.
    """

    schema_version: str
    qimen_mode: str
    fit_source: str
    baseline: OutcomeResearchPrediction
    adjusted_home_lambda: float
    adjusted_away_lambda: float
    raw_home_win_probability: float
    raw_draw_probability: float
    raw_away_win_probability: float
    home_win_probability: float
    draw_probability: float
    away_win_probability: float
    predicted_result: str
    decision_margin: float
    top_scorelines: tuple[ScoreProbability, ...]
    score_grid: tuple[ScoreProbability, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _result_probabilities(
    score_grid: tuple[ScoreProbability, ...],
) -> tuple[float, float, float]:
    home = sum(cell.probability for cell in score_grid if cell.home_goals > cell.away_goals)
    draw = sum(cell.probability for cell in score_grid if cell.home_goals == cell.away_goals)
    away = sum(cell.probability for cell in score_grid if cell.home_goals < cell.away_goals)
    return home, draw, away


def _brier_and_rps(
    probabilities: tuple[float, float, float],
    actual_result: str,
) -> tuple[float, float]:
    labels = ("主勝", "和局", "客勝")
    observed = tuple(1.0 if label == actual_result else 0.0 for label in labels)
    brier = sum((probability - target) ** 2 for probability, target in zip(probabilities, observed))
    rps = sum(
        (
            sum(probabilities[: index + 1])
            - sum(observed[: index + 1])
        ) ** 2
        for index in range(len(labels) - 1)
    ) / (len(labels) - 1)
    return brier, rps


def build_qimen_hybrid_prediction(
    model_input: PrematchModelInput,
    board: QimenBoard,
    reading: FootballReading,
    match: MatchInput,
    fit: QimenLambdaFit,
    *,
    venue_source: str,
    neutral_home_goals_per_match: float | None = None,
    neutral_away_goals_per_match: float | None = None,
) -> QimenHybridPrediction:
    """Build the football baseline and a fitted-Qimen challenger from one snapshot."""

    if not fit.converged_home or not fit.converged_away:
        raise ValueError("Qimen lambda fit 尚未收斂，不可建立 challenger")

    baseline = build_outcome_research_prediction(
        model_input,
        board,
        reading,
        match,
        venue_source=venue_source,
        neutral_home_goals_per_match=neutral_home_goals_per_match,
        neutral_away_goals_per_match=neutral_away_goals_per_match,
    )
    numeric_features = qimen_outcome_numeric_features(baseline.qimen_outcome_features)
    adjusted_home, adjusted_away = apply_qimen_lambda_adjustment(
        baseline.prediction.expected_home_goals,
        baseline.prediction.expected_away_goals,
        numeric_features,
        fit,
    )

    adjusted_shell = replace(
        baseline.prediction,
        expected_home_goals=adjusted_home,
        expected_away_goals=adjusted_away,
    )
    score_grid = reconstruct_score_grid(adjusted_shell)
    raw_home, raw_draw, raw_away = _result_probabilities(score_grid)

    if baseline.prediction.calibration_source:
        home, draw, away = temperature_scale_probabilities(
            (raw_home, raw_draw, raw_away),
            float(baseline.prediction.model_input["calibration_temperature"]),
        )
    else:
        home, draw, away = raw_home, raw_draw, raw_away

    outcomes = {"主勝": home, "和局": draw, "客勝": away}
    ordered = sorted(outcomes.items(), key=lambda item: item[1], reverse=True)
    top_scorelines = tuple(sorted(score_grid, key=lambda cell: cell.probability, reverse=True)[:5])
    return QimenHybridPrediction(
        schema_version=QIMEN_HYBRID_VERSION,
        qimen_mode="FITTED_RESEARCH_CHALLENGER",
        fit_source=fit.artifact_source,
        baseline=baseline,
        adjusted_home_lambda=adjusted_home,
        adjusted_away_lambda=adjusted_away,
        raw_home_win_probability=raw_home,
        raw_draw_probability=raw_draw,
        raw_away_win_probability=raw_away,
        home_win_probability=home,
        draw_probability=draw,
        away_win_probability=away,
        predicted_result=ordered[0][0],
        decision_margin=ordered[0][1] - ordered[1][1],
        top_scorelines=top_scorelines,
        score_grid=score_grid,
    )


def evaluate_paired_hybrid(
    prediction: QimenHybridPrediction,
    actual_home_goals: int,
    actual_away_goals: int,
) -> dict[str, Any]:
    """Score baseline and hybrid on the same match; negative deltas are better."""

    if actual_home_goals > actual_away_goals:
        actual_result = "主勝"
        baseline_probability = prediction.baseline.prediction.home_win_probability
        hybrid_probability = prediction.home_win_probability
    elif actual_home_goals < actual_away_goals:
        actual_result = "客勝"
        baseline_probability = prediction.baseline.prediction.away_win_probability
        hybrid_probability = prediction.away_win_probability
    else:
        actual_result = "和局"
        baseline_probability = prediction.baseline.prediction.draw_probability
        hybrid_probability = prediction.draw_probability

    baseline_vector = (
        prediction.baseline.prediction.home_win_probability,
        prediction.baseline.prediction.draw_probability,
        prediction.baseline.prediction.away_win_probability,
    )
    hybrid_vector = (
        prediction.home_win_probability,
        prediction.draw_probability,
        prediction.away_win_probability,
    )
    baseline_brier, baseline_rps = _brier_and_rps(baseline_vector, actual_result)
    hybrid_brier, hybrid_rps = _brier_and_rps(hybrid_vector, actual_result)

    baseline_exact_probability = exact_score_probability(
        prediction.baseline.score_grid,
        actual_home_goals,
        actual_away_goals,
    )
    hybrid_exact_probability = exact_score_probability(
        prediction.score_grid,
        actual_home_goals,
        actual_away_goals,
    )
    baseline_result_log_loss = -log(max(baseline_probability, 1e-15))
    hybrid_result_log_loss = -log(max(hybrid_probability, 1e-15))
    baseline_exact_nll = exact_score_log_loss(
        prediction.baseline.score_grid,
        actual_home_goals,
        actual_away_goals,
    )
    hybrid_exact_nll = exact_score_log_loss(
        prediction.score_grid,
        actual_home_goals,
        actual_away_goals,
    )

    return {
        "actual_result": actual_result,
        "actual_score": (actual_home_goals, actual_away_goals),
        "baseline_result_probability": baseline_probability,
        "hybrid_result_probability": hybrid_probability,
        "baseline_result_log_loss": baseline_result_log_loss,
        "hybrid_result_log_loss": hybrid_result_log_loss,
        "result_log_loss_delta": hybrid_result_log_loss - baseline_result_log_loss,
        "baseline_brier_score": baseline_brier,
        "hybrid_brier_score": hybrid_brier,
        "brier_score_delta": hybrid_brier - baseline_brier,
        "baseline_ranked_probability_score": baseline_rps,
        "hybrid_ranked_probability_score": hybrid_rps,
        "ranked_probability_score_delta": hybrid_rps - baseline_rps,
        "baseline_exact_score_probability": baseline_exact_probability,
        "hybrid_exact_score_probability": hybrid_exact_probability,
        "baseline_exact_score_nll": baseline_exact_nll,
        "hybrid_exact_score_nll": hybrid_exact_nll,
        "exact_score_nll_delta": hybrid_exact_nll - baseline_exact_nll,
        "fit_source": prediction.fit_source,
        "qimen_mode": prediction.qimen_mode,
        "note": "同一盤前快照 paired comparison；delta < 0 代表 hybrid 較佳。",
    }
