from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from qimen.models import CalendarContext


@pytest.fixture
def calendar_context() -> CalendarContext:
    zone = ZoneInfo("Asia/Taipei")
    event = datetime(2026, 1, 10, 20, 0, tzinfo=zone)
    return CalendarContext(
        local_datetime=event,
        timezone_name="Asia/Taipei",
        solar_term="小寒",
        solar_term_at=event - timedelta(days=5),
        next_solar_term="大寒",
        next_solar_term_at=event + timedelta(days=10),
        year_ganzhi="乙巳",
        month_ganzhi="己丑",
        day_ganzhi="甲子",
        hour_ganzhi="甲戌",
        day_xun="甲子旬",
        day_void_branches=("戌", "亥"),
        source="test-fixture",
    )
