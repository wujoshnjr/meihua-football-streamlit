from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from lunar_python import Solar

from models import CastingMoment


CASTING_TIMEZONE = "Asia/Taipei"


def _taipei_timezone() -> timezone | ZoneInfo:
    try:
        return ZoneInfo(CASTING_TIMEZONE)
    except ZoneInfoNotFoundError:
        # Taiwan has used UTC+08:00 without daylight saving time since 1979.
        return timezone(timedelta(hours=8), name=CASTING_TIMEZONE)


def _traditional(value: str) -> str:
    return value.replace("闰", "閏").replace("腊", "臘")


def build_casting_moment(value: datetime | None = None) -> CastingMoment:
    """Capture one immutable Gregorian/lunar timestamp in Taiwan time."""

    taipei = _taipei_timezone()
    if value is None:
        local = datetime.now(taipei)
    elif value.tzinfo is None:
        local = value.replace(tzinfo=taipei)
    else:
        local = value.astimezone(taipei)
    local = local.replace(microsecond=0)

    lunar = Solar.fromYmdHms(
        local.year,
        local.month,
        local.day,
        local.hour,
        local.minute,
        local.second,
    ).getLunar()
    lunar_year_chinese = _traditional(lunar.getYearInChinese())
    lunar_year_ganzhi = _traditional(lunar.getYearInGanZhi())
    lunar_month_text = _traditional(lunar.getMonthInChinese())
    lunar_day_text = _traditional(lunar.getDayInChinese())
    shichen = _traditional(lunar.getTimeZhi())
    shichen_ganzhi = _traditional(lunar.getTimeInGanZhi())
    lunar_text = (
        f"農曆{lunar_year_chinese}年（{lunar_year_ganzhi}年）"
        f"{lunar_month_text}月{lunar_day_text} {shichen_ganzhi}時（{shichen}時）"
    )

    return CastingMoment(
        timezone=CASTING_TIMEZONE,
        utc_offset="UTC+08:00",
        gregorian_iso=local.isoformat(timespec="seconds"),
        gregorian_text=local.strftime("%Y-%m-%d %H:%M:%S"),
        lunar_text=lunar_text,
        lunar_year=int(lunar.getYear()),
        lunar_year_chinese=lunar_year_chinese,
        lunar_year_ganzhi=lunar_year_ganzhi,
        lunar_month=abs(int(lunar.getMonth())),
        lunar_month_text=lunar_month_text,
        lunar_is_leap_month=int(lunar.getMonth()) < 0,
        lunar_day=int(lunar.getDay()),
        lunar_day_text=lunar_day_text,
        shichen=shichen,
        shichen_ganzhi=shichen_ganzhi,
    )


__all__ = ["CASTING_TIMEZONE", "build_casting_moment"]
