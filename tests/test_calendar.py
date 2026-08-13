from __future__ import annotations

from datetime import datetime

import pytest

from qimen.calendar import (
    SEXAGENARY,
    aware_local_datetime,
    normalize_term,
    sexagenary_index,
    xun_for,
)


def test_sexagenary_cycle_is_complete_and_unique():
    assert len(SEXAGENARY) == 60
    assert len(set(SEXAGENARY)) == 60
    assert SEXAGENARY[0] == "甲子"
    assert SEXAGENARY[-1] == "癸亥"


@pytest.mark.parametrize(
    ("ganzhi", "xun", "instrument", "void", "offset"),
    [
        ("甲子", "甲子旬", "戊", ("戌", "亥"), 0),
        ("癸酉", "甲子旬", "戊", ("戌", "亥"), 9),
        ("甲戌", "甲戌旬", "己", ("申", "酉"), 0),
        ("癸亥", "甲寅旬", "癸", ("子", "丑"), 9),
    ],
)
def test_xun_lookup(ganzhi, xun, instrument, void, offset):
    assert xun_for(ganzhi) == (xun, instrument, void, offset)


def test_invalid_ganzhi_rejected():
    with pytest.raises(ValueError):
        sexagenary_index("甲丑")


def test_term_normalization():
    assert normalize_term("惊蛰") == "驚蟄"
    assert normalize_term("冬至") == "冬至"


def test_local_time_is_timezone_aware():
    local = aware_local_datetime(datetime(2026, 8, 13, 20, 0), "Asia/Taipei")
    assert local.tzinfo is not None
    assert local.utcoffset().total_seconds() == 8 * 3600


def test_nonexistent_dst_wall_time_rejected():
    with pytest.raises(ValueError, match="不存在"):
        aware_local_datetime(datetime(2026, 3, 29, 1, 30), "Europe/London")
