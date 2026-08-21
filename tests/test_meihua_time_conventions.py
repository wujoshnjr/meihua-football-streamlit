from datetime import datetime
from zoneinfo import ZoneInfo

from meihua.engine import (
    LEAP_MONTH_POLICY,
    LUNAR_DAY_BOUNDARY_POLICY,
    build_meihua_snapshot_from_numbers,
)


def _cast(month: int):
    return build_meihua_snapshot_from_numbers(
        event_local_at=datetime(2026, 1, 1, 8, 0, tzinfo=ZoneInfo("Asia/Taipei")),
        timezone_name="Asia/Taipei",
        year_branch="午",
        lunar_month=month,
        lunar_day=12,
        hour_branch="辰",
    )


def test_leap_month_raw_sign_is_preserved_but_base_month_number_is_used():
    regular = _cast(5)
    leap = _cast(-5)

    assert regular.lunar_month_raw == 5
    assert regular.lunar_month_is_leap is False
    assert leap.lunar_month_raw == -5
    assert leap.lunar_month_is_leap is True
    assert regular.lunar_month == leap.lunar_month == 5
    assert regular.leap_month_policy == leap.leap_month_policy == LEAP_MONTH_POLICY
    assert regular.upper_trigram == leap.upper_trigram
    assert regular.lower_trigram == leap.lower_trigram
    assert regular.moving_line == leap.moving_line


def test_lunar_day_boundary_policy_is_explicit_in_snapshot():
    snapshot = _cast(5)
    assert snapshot.lunar_day_boundary_policy == LUNAR_DAY_BOUNDARY_POLICY
    payload = snapshot.to_dict()
    assert payload["leap_month_policy"] == "LEAP_MONTH_USES_BASE_MONTH_NUMBER"
    assert payload["lunar_day_boundary_policy"] == "EVENT_LOCATION_CIVIL_WALL_DATE_TO_LUNAR_PYTHON"
    assert payload["schema_version"] == "jarvis-meihua-year-month-day-hour-v0.3.0"
