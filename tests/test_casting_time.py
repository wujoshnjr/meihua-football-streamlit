from __future__ import annotations

from datetime import datetime, timezone

from casting_time import CASTING_TIMEZONE, build_casting_moment


def test_casting_moment_converts_utc_to_taipei_lunar_time() -> None:
    moment = build_casting_moment(datetime(2026, 7, 13, 7, 30, tzinfo=timezone.utc))

    assert moment.timezone == CASTING_TIMEZONE
    assert moment.utc_offset == "UTC+08:00"
    assert moment.gregorian_iso == "2026-07-13T15:30:00+08:00"
    assert moment.gregorian_text == "2026-07-13 15:30:00"
    assert moment.lunar_year == 2026
    assert moment.lunar_year_ganzhi == "丙午"
    assert moment.lunar_month == 5
    assert moment.lunar_month_text == "五"
    assert moment.lunar_day == 29
    assert moment.lunar_day_text == "廿九"
    assert moment.shichen == "申"
    assert moment.shichen_ganzhi == "庚申"
    assert moment.lunar_text == "農曆二〇二六年（丙午年）五月廿九 庚申時（申時）"


def test_casting_moment_uses_traditional_leap_month_label() -> None:
    moment = build_casting_moment(datetime(2025, 7, 25, 12, 0))

    assert moment.lunar_is_leap_month is True
    assert moment.lunar_month == 6
    assert moment.lunar_month_text == "閏六"
    assert "閏六月初一" in moment.lunar_text
