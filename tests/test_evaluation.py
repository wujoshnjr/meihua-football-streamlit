from __future__ import annotations

from datetime import timedelta

import pytest

from qimen.engine import cast_qimen
from qimen.evaluation import evaluate_scenarios, lock_scenarios
from qimen.football import interpret_football


def test_scenarios_must_be_locked_prematch(calendar_context):
    board = cast_qimen(calendar_context.local_datetime, calendar_context.timezone_name, calendar=calendar_context)
    reading = interpret_football(board)
    with pytest.raises(ValueError, match="開賽前"):
        lock_scenarios("TEST", calendar_context.local_datetime, calendar_context.local_datetime, reading)


def test_qualitative_top_k_evaluation(calendar_context):
    board = cast_qimen(calendar_context.local_datetime, calendar_context.timezone_name, calendar=calendar_context)
    reading = interpret_football(board)
    locked = lock_scenarios(
        "TEST", calendar_context.local_datetime,
        calendar_context.local_datetime - timedelta(hours=8), reading,
    )
    result = evaluate_scenarios(locked, [reading.scenarios[0].title], top_k=3)
    assert result["precision_at_k"] == pytest.approx(1 / 3)
    assert "不回推出勝率" in result["note"]
