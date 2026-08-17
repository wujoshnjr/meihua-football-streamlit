from __future__ import annotations

from qimen.engine import cast_qimen
from qimen.football import interpret_football
from qimen.outcome_design import qimen_outcome_numeric_features
from qimen.outcome_features import build_qimen_outcome_feature_snapshot


def test_numeric_design_is_deterministic_and_contains_no_interpretation_weight(calendar_context):
    board = cast_qimen(
        calendar_context.local_datetime,
        calendar_context.timezone_name,
        calendar=calendar_context,
    )
    reading = interpret_football(board)
    snapshot = build_qimen_outcome_feature_snapshot(board, reading)

    first = qimen_outcome_numeric_features(snapshot)
    second = qimen_outcome_numeric_features(snapshot)

    assert first == second
    assert "same_palace" in first
    assert "fu_yin_count" in first
    assert any(name.startswith("home_door::") for name in first)
    assert any(name.startswith("away_star::") for name in first)
    assert all("interpretation_index" not in name for name in first)
    assert all(isinstance(value, float) for value in first.values())

    # Reference categories are intentionally omitted so one-of-K groups cannot
    # sum to a constant one and recreate an intercept in the residual model.
    assert "home_door::休門" not in first
    assert "away_door::休門" not in first
    assert "chief_door::休門" not in first
    assert "home_deity::值符" not in first
    assert "away_deity::值符" not in first
    assert "home_season::旺" not in first
    assert "away_season::旺" not in first
