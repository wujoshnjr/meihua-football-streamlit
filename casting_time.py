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


def _utc_offset_text(value: datetime) -> str:
    offset = value.utcoffset()
    if offset is None:
        raise ValueError("時間必須包含可解析的 UTC 位移。")
    total_minutes = int(offset.total_seconds() // 60)
    sign = "+" if total_minutes >= 0 else "-"
    hours, minutes = divmod(abs(total_minutes), 60)
    return f"UTC{sign}{hours:02d}:{minutes:02d}"


def _build_moment(local: datetime, timezone_name: str) -> CastingMoment:
    """Build the shared Gregorian/lunar representation from one local civil time."""

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
    day_ganzhi = _traditional(lunar.getDayInGanZhi())
    day_stem = day_ganzhi[0]
    day_branch = day_ganzhi[1]
    shichen = _traditional(lunar.getTimeZhi())
    shichen_ganzhi = _traditional(lunar.getTimeInGanZhi())
    lunar_text = (
        f"農曆{lunar_year_chinese}年（{lunar_year_ganzhi}年）"
        f"{lunar_month_text}月{lunar_day_text} {shichen_ganzhi}時（{shichen}時）"
    )

    return CastingMoment(
        timezone=timezone_name,
        utc_offset=_utc_offset_text(local),
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
        day_ganzhi=day_ganzhi,
        day_stem=day_stem,
        day_branch=day_branch,
        shichen=shichen,
        shichen_ganzhi=shichen_ganzhi,
    )


def build_casting_moment(value: datetime | None = None) -> CastingMoment:
    """Capture the actual execution timestamp in Taiwan time for audit only."""

    taipei = _taipei_timezone()
    if value is None:
        local = datetime.now(taipei)
    elif value.tzinfo is None:
        local = value.replace(tzinfo=taipei)
    else:
        local = value.astimezone(taipei)
    return _build_moment(local, CASTING_TIMEZONE)


def build_event_moment(value: datetime, timezone_name: str = "") -> CastingMoment:
    """Build the sole divination-time environment from official ``event_at``.

    ``event_at`` must be timezone-aware unless an IANA timezone is supplied.  Its
    local civil clock is intentionally preserved because day, lunar month and
    hour branch belong to the event environment, not to the later execution.
    """

    requested_timezone = timezone_name.strip()
    if requested_timezone:
        try:
            event_timezone = ZoneInfo(requested_timezone)
        except ZoneInfoNotFoundError as exc:
            raise ValueError(f"無法辨識事件時區：{requested_timezone}") from exc
        local = (
            value.replace(tzinfo=event_timezone)
            if value.tzinfo is None
            else value.astimezone(event_timezone)
        )
        label = requested_timezone
    else:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("event_at 必須包含 UTC 位移，或另填 IANA 事件時區。")
        local = value
        label = _utc_offset_text(local)
    return _build_moment(local, label)


__all__ = ["CASTING_TIMEZONE", "build_casting_moment", "build_event_moment"]
