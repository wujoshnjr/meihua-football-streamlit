from __future__ import annotations

from datetime import timedelta

import pytest

from qimen.engine import cast_qimen
from qimen.football import interpret_football
from qimen.outcome_prediction import (
    build_outcome_research_prediction,
    evaluate_exact_score,
)
from qimen.prediction import PrematchModelInput, TeamForm
from qimen.protocol import MatchInput


def _board_and_reading(calendar_context):
    board = cast_qimen(
        calendar_context.local_datetime,
        calendar_context.timezone_name,
        calendar=calendar_context,
    )
    return board, interpret_football(board)


def _model_input(calendar_context):
    return PrematchModelInput(
        home=TeamForm(10, 1.35, 1.35),
        away=TeamForm(10, 1.35, 1.35),
        league_home_goals_per_match=1.50,
        league_away_goals_per_match=1.20,
        data_as_of=calendar_context.local_datetime - timedelta(days=1),
        data_source="test-fixture",
    )


def _match(calendar_context, venue_mode):
    return MatchInput(
        match_id=f"VENUE-{venue_mode}",
        home_team="Home",
        away_team="Away",
        competition="International Cup",
        event_at=calendar_context.local_datetime,
        timezone_name=calendar_context.timezone_name,
        venue="Test Stadium",
        city="Test City",
        venue_mode=venue_mode,
    )


def test_neutral_match_does_not_inherit_nominal_home_advantage(calendar_context):
    board, reading = _board_and_reading(calendar_context)
    result = build_outcome_research_prediction(
        _model_input(calendar_context),
        board,
        reading,
        _match(calendar_context, "NEUTRAL"),
        venue_source="neutral-training-artifact:test",
        neutral_home_goals_per_match=1.30,
        neutral_away_goals_per_match=1.30,
    )

    assert result.venue_baseline.venue_mode == "NEUTRAL"
    assert result.prediction.expected_home_goals == pytest.approx(
        result.prediction.expected_away_goals
    )
    assert result.prediction.qimen_mode == "SHADOW_ONLY"
    assert len(result.score_grid) == 121
    assert sum(cell.probability for cell in result.score_grid) == pytest.approx(1.0)


def test_true_home_retains_registered_home_baseline(calendar_context):
    board, reading = _board_and_reading(calendar_context)
    result = build_outcome_research_prediction(
        _model_input(calendar_context),
        board,
        reading,
        _match(calendar_context, "TRUE_HOME"),
        venue_source="league-training-artifact:test",
    )

    assert result.venue_baseline.home_goals_per_match == pytest.approx(1.50)
    assert result.venue_baseline.away_goals_per_match == pytest.approx(1.20)
    assert result.prediction.expected_home_goals > result.prediction.expected_away_goals


def test_neutral_match_requires_explicit_neutral_rates(calendar_context):
    board, reading = _board_and_reading(calendar_context)
    with pytest.raises(ValueError, match="中立場必須提供"):
        build_outcome_research_prediction(
            _model_input(calendar_context),
            board,
            reading,
            _match(calendar_context, "NEUTRAL"),
            venue_source="neutral-training-artifact:test",
        )


def test_exact_score_evaluation_uses_full_grid(calendar_context):
    board, reading = _board_and_reading(calendar_context)
    result = build_outcome_research_prediction(
        _model_input(calendar_context),
        board,
        reading,
        _match(calendar_context, "NEUTRAL"),
        venue_source="neutral-training-artifact:test",
        neutral_home_goals_per_match=1.25,
        neutral_away_goals_per_match=1.25,
    )

    evaluation = evaluate_exact_score(result, 1, 1)
    assert 0 < evaluation["exact_score_probability"] < 1
    assert evaluation["exact_score_log_loss"] > 0
    assert evaluation["score_grid_cells"] == 121
    assert evaluation["venue_mode"] == "NEUTRAL"
    assert evaluation["qimen_mode"] == "SHADOW_ONLY"
