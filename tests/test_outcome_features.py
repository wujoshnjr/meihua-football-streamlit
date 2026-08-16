from qimen.engine import cast_qimen
from qimen.football import interpret_football
from qimen.outcome_features import (
    QIMEN_OUTCOME_FEATURE_VERSION,
    build_qimen_outcome_feature_snapshot,
)


def test_outcome_features_preserve_raw_qimen_facts(calendar_context):
    board = cast_qimen(
        calendar_context.local_datetime,
        calendar_context.timezone_name,
        calendar=calendar_context,
    )
    reading = interpret_football(board)

    snapshot = build_qimen_outcome_feature_snapshot(board, reading)

    assert snapshot.feature_version == QIMEN_OUTCOME_FEATURE_VERSION
    assert snapshot.home_original_stem == board.calendar.day_ganzhi[0]
    assert snapshot.away_original_stem == board.calendar.hour_ganzhi[0]
    assert snapshot.home_visible_stem == reading.home.stem
    assert snapshot.away_visible_stem == reading.away.stem
    assert snapshot.home_palace == reading.home.palace
    assert snapshot.away_palace == reading.away.palace
    assert snapshot.same_palace == (reading.home.palace == reading.away.palace)
    assert snapshot.direction_resolution == (
        "LOW_SAME_PALACE" if snapshot.same_palace else "NORMAL"
    )


def test_outcome_features_do_not_convert_interpretation_index_to_result_weight(calendar_context):
    board = cast_qimen(
        calendar_context.local_datetime,
        calendar_context.timezone_name,
        calendar=calendar_context,
    )
    reading = interpret_football(board)

    snapshot = build_qimen_outcome_feature_snapshot(board, reading)
    payload = snapshot.to_dict()

    assert payload["home_interpretation_index"] == reading.home.signal_index
    assert payload["away_interpretation_index"] == reading.away.signal_index
    assert "home_win_probability" not in payload
    assert "away_win_probability" not in payload
    assert "expected_home_goals" not in payload
    assert "expected_away_goals" not in payload


def test_pattern_counters_are_deterministic(calendar_context):
    board = cast_qimen(
        calendar_context.local_datetime,
        calendar_context.timezone_name,
        calendar=calendar_context,
    )
    reading = interpret_football(board)

    first = build_qimen_outcome_feature_snapshot(board, reading)
    second = build_qimen_outcome_feature_snapshot(board, reading)

    assert first == second
    assert first.pattern_names == tuple(sorted(pattern.name for pattern in board.patterns))
    assert first.fu_yin_count >= 0
    assert first.fan_yin_count >= 0
    assert first.punishment_count >= 0
    assert first.pressure_count >= 0
    assert first.grave_count >= 0
    assert first.tianwang_count >= 0
