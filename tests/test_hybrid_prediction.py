from __future__ import annotations

from datetime import timedelta

import pytest

from qimen.engine import cast_qimen
from qimen.football import interpret_football
from qimen.hybrid_prediction import (
    build_qimen_hybrid_prediction,
    evaluate_paired_hybrid,
)
from qimen.lambda_adjustment import QimenLambdaFit
from qimen.outcome_design import qimen_outcome_numeric_features
from qimen.outcome_features import build_qimen_outcome_feature_snapshot
from qimen.prediction import PrematchModelInput, TeamForm
from qimen.protocol import MatchInput


def _context(calendar_context):
    board = cast_qimen(
        calendar_context.local_datetime,
        calendar_context.timezone_name,
        calendar=calendar_context,
    )
    reading = interpret_football(board)
    model_input = PrematchModelInput(
        home=TeamForm(10, 1.35, 1.35),
        away=TeamForm(10, 1.35, 1.35),
        league_home_goals_per_match=1.50,
        league_away_goals_per_match=1.20,
        data_as_of=calendar_context.local_datetime - timedelta(days=1),
        data_source="test-fixture",
    )
    match = MatchInput(
        match_id="HYBRID-001",
        home_team="Home",
        away_team="Away",
        competition="Test League",
        event_at=calendar_context.local_datetime,
        timezone_name=calendar_context.timezone_name,
        venue="Test Stadium",
        city="Taipei",
        venue_mode="TRUE_HOME",
    )
    return board, reading, model_input, match


def _fit(board, reading, *, converged=True):
    snapshot = build_qimen_outcome_feature_snapshot(board, reading)
    features = qimen_outcome_numeric_features(snapshot)
    names = tuple(sorted(features))
    active_name = next(name for name in names if features[name] == 1.0)
    home = tuple(0.12 if name == active_name else 0.0 for name in names)
    away = tuple(0.0 for _ in names)
    return QimenLambdaFit(
        schema_version="test-fit",
        git_commit="test",
        feature_names=names,
        home_coefficients=home,
        away_coefficients=away,
        l2_penalty=10.0,
        matches=500,
        training_started_at=board.calendar.local_datetime - timedelta(days=500),
        training_ended_at=board.calendar.local_datetime - timedelta(days=1),
        converged_home=converged,
        converged_away=converged,
        iterations_home=3,
        iterations_away=3,
        training_data_sha256="a" * 64,
        artifact_sha256="b" * 64,
    )


def test_hybrid_adjusts_only_challenger_not_baseline(calendar_context):
    board, reading, model_input, match = _context(calendar_context)
    result = build_qimen_hybrid_prediction(
        model_input,
        board,
        reading,
        match,
        _fit(board, reading),
        venue_source="league-test",
    )

    assert result.qimen_mode == "FITTED_RESEARCH_CHALLENGER"
    assert result.baseline.prediction.qimen_mode == "SHADOW_ONLY"
    assert result.adjusted_home_lambda > result.baseline.prediction.expected_home_goals
    assert result.adjusted_away_lambda == pytest.approx(
        result.baseline.prediction.expected_away_goals
    )
    assert len(result.score_grid) == 121
    assert sum(cell.probability for cell in result.score_grid) == pytest.approx(1.0)
    assert result.fit_source.startswith("qimen-lambda-fit:")


def test_paired_evaluation_reports_same_match_deltas(calendar_context):
    board, reading, model_input, match = _context(calendar_context)
    result = build_qimen_hybrid_prediction(
        model_input,
        board,
        reading,
        match,
        _fit(board, reading),
        venue_source="league-test",
    )
    evaluation = evaluate_paired_hybrid(result, 2, 1)

    assert evaluation["actual_result"] == "主勝"
    assert evaluation["actual_score"] == (2, 1)
    assert evaluation["hybrid_result_probability"] != pytest.approx(
        evaluation["baseline_result_probability"]
    )
    assert evaluation["hybrid_exact_score_probability"] != pytest.approx(
        evaluation["baseline_exact_score_probability"]
    )
    assert "result_log_loss_delta" in evaluation
    assert "exact_score_nll_delta" in evaluation


def test_unconverged_fit_is_rejected(calendar_context):
    board, reading, model_input, match = _context(calendar_context)
    with pytest.raises(ValueError, match="尚未收斂"):
        build_qimen_hybrid_prediction(
            model_input,
            board,
            reading,
            match,
            _fit(board, reading, converged=False),
            venue_source="league-test",
        )
