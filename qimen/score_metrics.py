from __future__ import annotations

from math import isfinite, log
from typing import Iterable, Protocol


class ScoreCell(Protocol):
    home_goals: int
    away_goals: int
    probability: float


def exact_score_probability(
    score_grid: Iterable[ScoreCell],
    actual_home_goals: int,
    actual_away_goals: int,
) -> float:
    """Return the probability assigned to the observed exact score."""

    if (
        isinstance(actual_home_goals, bool)
        or isinstance(actual_away_goals, bool)
        or not isinstance(actual_home_goals, int)
        or not isinstance(actual_away_goals, int)
        or actual_home_goals < 0
        or actual_away_goals < 0
    ):
        raise ValueError("實際進球必須為非負整數")

    probability = 0.0
    for cell in score_grid:
        if not isfinite(cell.probability) or cell.probability < 0 or cell.probability > 1:
            raise ValueError("比分矩陣機率必須介於 0 與 1")
        if cell.home_goals == actual_home_goals and cell.away_goals == actual_away_goals:
            probability += cell.probability
    return probability


def exact_score_log_loss(
    score_grid: Iterable[ScoreCell],
    actual_home_goals: int,
    actual_away_goals: int,
    *,
    floor: float = 1e-15,
) -> float:
    """Score the full exact-score distribution with negative log likelihood."""

    if not isfinite(floor) or not 0 < floor < 1:
        raise ValueError("floor 必須介於 0 與 1")
    probability = exact_score_probability(score_grid, actual_home_goals, actual_away_goals)
    return -log(max(probability, floor))
