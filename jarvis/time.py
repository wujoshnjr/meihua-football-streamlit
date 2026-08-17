from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


class EventLocalTimeError(ValueError):
    pass


def aware_event_local_datetime(
    value: datetime,
    timezone_name: str,
    *,
    fold: int = 0,
) -> datetime:
    """Return a validated event-location civil datetime.

    A naive datetime is interpreted in ``timezone_name``. Aware values are
    converted into that zone. Non-existent DST wall times are rejected rather
    than silently attaching an invalid offset.
    """

    try:
        zone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise EventLocalTimeError(f"找不到 IANA 時區：{timezone_name}") from exc

    if value.tzinfo is not None:
        return value.astimezone(zone)

    candidate = value.replace(tzinfo=zone, fold=fold)
    roundtrip = candidate.astimezone(ZoneInfo("UTC")).astimezone(zone)
    if roundtrip.replace(tzinfo=None) != value:
        raise EventLocalTimeError(f"{value.isoformat()} 在 {timezone_name} 是不存在的夏令時間")
    return candidate
