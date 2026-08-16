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
