from datetime import datetime
from zoneinfo import ZoneInfo

from meihua import build_meihua_snapshot, build_meihua_snapshot_from_numbers
from qimen.engine import cast_qimen


def test_qimen_engine_builds_complete_nine_palace_board():
    event = datetime(2026, 6, 15, 12, 0, tzinfo=ZoneInfo("America/New_York"))
    board = cast_qimen(event, "America/New_York")

    assert set(board.palaces) == set(range(1, 10))
    assert board.dun in {"陽遁", "陰遁"}
    assert 1 <= board.ju <= 9
    assert board.chief_star
    assert board.chief_door
    assert sum(1 for state in board.palaces.values() if state.is_horse) == 1


def test_meihua_engine_is_reproducible_for_same_event():
    event = datetime(2026, 6, 15, 12, 0, tzinfo=ZoneInfo("America/New_York"))
    first = build_meihua_snapshot(event, "America/New_York")
    second = build_meihua_snapshot(event, "America/New_York")

    assert first == second
    assert 1 <= first.moving_line <= 6
    assert first.body_use_relation in {"生體", "體生用", "克體", "體克用", "比和"}
    assert first.body_season_state in {"旺", "平", "衰"}


def test_meihua_numeric_cast_uses_mod_eight_and_mod_six_contract():
    event = datetime(2026, 1, 1, 8, 0, tzinfo=ZoneInfo("Asia/Taipei"))
    result = build_meihua_snapshot_from_numbers(
        event_local_at=event,
        timezone_name="Asia/Taipei",
        year_branch="午",
        lunar_month=5,
        lunar_day=12,
        hour_branch="辰",
    )

    assert result.upper_trigram in {"乾", "兌", "離", "震", "巽", "坎", "艮", "坤"}
    assert result.lower_trigram in {"乾", "兌", "離", "震", "巽", "坎", "艮", "坤"}
    assert 1 <= result.moving_line <= 6
