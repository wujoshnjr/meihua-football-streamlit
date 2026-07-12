from __future__ import annotations

import math
from typing import Any, Mapping

from models import MatchInput


BASE_TOTAL_GOALS = 2.55
MAX_SCORE_GOALS = 10


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def safe_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def poisson_probability(goals: int, expected_goals: float) -> float:
    if goals < 0:
        return 0.0
    return math.exp(-expected_goals) * (expected_goals**goals) / math.factorial(goals)


def score_outcome(score: tuple[int, int]) -> str:
    if score[0] > score[1]:
        return "體方勝"
    if score[0] < score[1]:
        return "用方勝"
    return "平局"


def poisson_grid(
    body_lambda: float,
    use_lambda: float,
    max_goals: int = MAX_SCORE_GOALS,
) -> tuple[list[dict[str, Any]], float]:
    """Return a normalized independent-Poisson score grid and omitted tail mass."""
    raw: list[tuple[tuple[int, int], float]] = []
    for body_goals in range(max_goals + 1):
        body_probability = poisson_probability(body_goals, body_lambda)
        for use_goals in range(max_goals + 1):
            probability = body_probability * poisson_probability(use_goals, use_lambda)
            raw.append(((body_goals, use_goals), probability))

    captured_mass = sum(probability for _, probability in raw)
    normalizer = captured_mass or 1.0
    raw.sort(key=lambda item: item[1], reverse=True)
    grid = [
        {
            "score": f"{score[0]}-{score[1]}",
            "body_goals": score[0],
            "use_goals": score[1],
            "probability": probability / normalizer,
            "outcome": score_outcome(score),
            "rank": index + 1,
        }
        for index, (score, probability) in enumerate(raw)
    ]
    return grid, max(0.0, 1.0 - captured_mass)


def outcome_probabilities(grid: list[Mapping[str, Any]]) -> dict[str, float]:
    probabilities = {"體方勝": 0.0, "平局": 0.0, "用方勝": 0.0}
    for row in grid:
        label = str(row.get("outcome", ""))
        if label in probabilities:
            probabilities[label] += safe_float(row.get("probability"), 0.0)
    return {key: round(value, 6) for key, value in probabilities.items()}


def top_scores(grid: list[Mapping[str, Any]], limit: int = 3) -> list[tuple[int, int]]:
    output: list[tuple[int, int]] = []
    for row in grid:
        try:
            score = (int(row["body_goals"]), int(row["use_goals"]))
        except (KeyError, TypeError, ValueError):
            continue
        if score not in output:
            output.append(score)
        if len(output) >= limit:
            break
    return output


def build_football_prior(match: MatchInput | None) -> dict[str, Any]:
    """Build football-only expected goals before any hexagram information is used.

    The 0-100 ratings determine the goal-share gap. Confidence shrinks uncertain
    ratings back toward an even match. A large, credible mismatch also widens the
    total-goal prior slightly so the model retains a meaningful high-score tail.
    """
    body_rating = clamp(safe_float(getattr(match, "body_strength_rating", 50.0), 50.0), 0.0, 100.0)
    use_rating = clamp(safe_float(getattr(match, "use_strength_rating", 50.0), 50.0), 0.0, 100.0)
    confidence = clamp(safe_float(getattr(match, "prior_confidence", 0.0), 0.0), 0.0, 1.0)
    venue = str(getattr(match, "venue", "中立場") or "中立場")

    signed_gap = (body_rating - use_rating) / 100.0
    effective_gap = signed_gap * confidence
    total_lambda = clamp(BASE_TOTAL_GOALS + 1.15 * abs(effective_gap), 2.20, 3.55)
    body_share = 0.50 + 0.42 * effective_gap
    venue_share_shift = 0.0
    if "體方主場" in venue:
        venue_share_shift = 0.04 * confidence
    elif "用方主場" in venue:
        venue_share_shift = -0.04 * confidence
    body_share = clamp(body_share + venue_share_shift, 0.18, 0.82)

    body_lambda = clamp(total_lambda * body_share, 0.15, 4.80)
    use_lambda = clamp(total_lambda * (1.0 - body_share), 0.15, 4.80)
    grid, tail_mass = poisson_grid(body_lambda, use_lambda)
    probabilities = outcome_probabilities(grid)

    return {
        "body_strength_rating": round(body_rating, 2),
        "use_strength_rating": round(use_rating, 2),
        "prior_confidence": round(confidence, 3),
        "venue": venue,
        "rating_gap": round(body_rating - use_rating, 2),
        "effective_gap": round(effective_gap, 4),
        "base_total_goals": BASE_TOTAL_GOALS,
        "total_lambda": round(body_lambda + use_lambda, 4),
        "body_lambda": round(body_lambda, 4),
        "use_lambda": round(use_lambda, 4),
        "body_goal_share": round(body_share, 4),
        "venue_share_shift": round(venue_share_shift, 4),
        "scores": [list(score) for score in top_scores(grid, 3)],
        "outcome_probabilities": probabilities,
        "tail_mass_above_grid": round(tail_mass, 8),
        "max_score_goals": MAX_SCORE_GOALS,
        "method": "football-prior-v1",
    }


__all__ = [
    "BASE_TOTAL_GOALS",
    "MAX_SCORE_GOALS",
    "build_football_prior",
    "clamp",
    "outcome_probabilities",
    "poisson_grid",
    "poisson_probability",
    "safe_float",
    "score_outcome",
    "top_scores",
]
