from __future__ import annotations

from qimen.engine import cast_qimen
from qimen.football import (
    SEASONAL_RULE_VERSION,
    interpret_football,
    locate_use_stem,
    seasonal_state,
)


def test_fixed_home_away_mapping_and_boundaries(calendar_context):
    board = cast_qimen(
        calendar_context.local_datetime,
        calendar_context.timezone_name,
        calendar=calendar_context,
    )
    reading = interpret_football(board)
    assert reading.home.role == "主隊／日干"
    assert reading.away.role == "客隊／時干"
    assert reading.home.palace == board.chief_star_palace  # 甲日
    assert reading.away.palace == board.chief_star_palace  # 甲時
    assert len(reading.scenarios) == 5
    assert [item.rank for item in reading.scenarios] == [1, 2, 3, 4, 5]
    assert "不自動產生" in reading.disclaimer
    assert "勝率" in reading.disclaimer
    assert "固定比分" in reading.disclaimer
    assert reading.mapping_version == "football-semantic-composition-v2.0.0"
    assert reading.home.football_meaning.observable_signals
    assert reading.home.football_meaning.counter_signals
    assert reading.away.football_meaning.observable_signals
    assert reading.seasonal_rule_version == SEASONAL_RULE_VERSION


def test_every_visible_stem_can_be_located(calendar_context):
    board = cast_qimen(
        calendar_context.local_datetime,
        calendar_context.timezone_name,
        calendar=calendar_context,
    )
    for stem in "乙丙丁戊己庚辛壬癸":
        assert locate_use_stem(board, stem) in range(1, 10)


def test_nine_star_season_uses_month_branch_classical_table():
    assert seasonal_state("水", "未") == ("囚", -1)
    assert seasonal_state("土", "未") == ("旺", 2)
    assert seasonal_state("水", "寅") == ("相", 1)
    assert seasonal_state("水", "申") == ("廢", -2)
