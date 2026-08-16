from dataclasses import dataclass
from math import log

import pytest

from qimen.score_metrics import exact_score_log_loss, exact_score_probability


@dataclass(frozen=True)
class Cell:
    home_goals: int
    away_goals: int
    probability: float


def test_exact_score_probability_reads_full_distribution():
    grid = (
        Cell(0, 0, 0.20),
        Cell(1, 0, 0.30),
        Cell(1, 1, 0.25),
        Cell(2, 1, 0.25),
    )

    assert exact_score_probability(grid, 1, 1) == pytest.approx(0.25)
    assert exact_score_log_loss(grid, 1, 1) == pytest.approx(-log(0.25))


def test_exact_score_probability_is_zero_when_score_is_outside_grid():
    grid = (Cell(0, 0, 0.5), Cell(1, 0, 0.5))

    assert exact_score_probability(grid, 4, 3) == 0.0
    assert exact_score_log_loss(grid, 4, 3) == pytest.approx(-log(1e-15))


def test_invalid_score_probability_is_rejected():
    grid = (Cell(0, 0, 1.1),)

    with pytest.raises(ValueError, match="比分矩陣機率"):
        exact_score_probability(grid, 0, 0)
