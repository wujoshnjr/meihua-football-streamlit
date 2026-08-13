from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from qimen.models import CalendarContext  # noqa: E402


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
