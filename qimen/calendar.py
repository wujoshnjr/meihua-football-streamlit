from __future__ import annotations

from datetime import datetime
from importlib import metadata
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .constants import BRANCHES, STEMS, TERM_NORMALIZATION, XUN_HEADS
from .models import CalendarContext


class CalendarDependencyError(RuntimeError):
    pass


class LocalTimeError(ValueError):
    pass


def normalize_term(name: str) -> str:
    return TERM_NORMALIZATION.get(name, name)


def detect_tzdb_version() -> str:
    """Record the timezone ruleset actually available to Python.

    Python may use the ``tzdata`` wheel or the operating system database. We
    report what is installed and never claim the latest IANA release merely
    because it exists upstream.
    """

    try:
        return f"tzdata-wheel-{metadata.version('tzdata')}"
    except metadata.PackageNotFoundError:
        pass

    for candidate in (
        Path("/usr/share/zoneinfo/tzdata.zi"),
        Path("/usr/share/lib/zoneinfo/tzdata.zi"),
    ):
        try:
            first_line = candidate.read_text(encoding="utf-8").splitlines()[0]
        except (OSError, IndexError):
            continue
        marker = "# version "
        if first_line.startswith(marker):
            return f"system-{first_line.removeprefix(marker).strip()}"
    return "system-unpinned"


def sexagenary_cycle() -> tuple[str, ...]:
    return tuple(STEMS[i % 10] + BRANCHES[i % 12] for i in range(60))


SEXAGENARY = sexagenary_cycle()


def sexagenary_index(ganzhi: str) -> int:
    try:
        return SEXAGENARY.index(ganzhi)
    except ValueError as exc:
        raise ValueError(f"無效干支：{ganzhi}") from exc


def xun_for(ganzhi: str) -> tuple[str, str, tuple[str, str], int]:
    index = sexagenary_index(ganzhi)
    group = index // 10
    name, instrument, void = XUN_HEADS[group]
    return name, instrument, void, index % 10


def aware_local_datetime(
    value: datetime,
    timezone_name: str,
    *,
    fold: int = 0,
) -> datetime:
    """Return a validated local civil datetime.

    A naive datetime is interpreted in ``timezone_name``. Aware values are converted
    into that zone. Non-existent DST wall times are rejected instead of silently
    moving the event to a different hour.
    """

    try:
        zone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise LocalTimeError(f"找不到 IANA 時區：{timezone_name}") from exc

    if value.tzinfo is not None:
        return value.astimezone(zone)

    candidate = value.replace(tzinfo=zone, fold=fold)
    roundtrip = candidate.astimezone(ZoneInfo("UTC")).astimezone(zone)
    if roundtrip.replace(tzinfo=None) != value:
        raise LocalTimeError(f"{value.isoformat()} 在 {timezone_name} 是不存在的夏令時間")
    return candidate


def _solar_to_datetime(solar, zone: ZoneInfo) -> datetime:
    return datetime(
        solar.getYear(), solar.getMonth(), solar.getDay(),
        solar.getHour(), solar.getMinute(), solar.getSecond(),
        tzinfo=zone,
    )


def build_calendar_context(local_datetime: datetime, timezone_name: str) -> CalendarContext:
    """Build pillars and exact solar-term context.

    ``lunar_python`` publishes solar-term instants in China Standard Time. The event
    instant is therefore converted to Asia/Shanghai for term/year/month boundaries,
    while day and hour pillars follow the configured event-location civil time.
    """

    try:
        from lunar_python import Solar
    except ImportError as exc:
        raise CalendarDependencyError(
            "缺少 lunar_python==1.4.8；請先安裝 requirements.txt"
        ) from exc

    local = aware_local_datetime(local_datetime, timezone_name)
    shanghai_zone = ZoneInfo("Asia/Shanghai")
    shanghai = local.astimezone(shanghai_zone)

    local_lunar = Solar.fromYmdHms(
        local.year, local.month, local.day, local.hour, local.minute, local.second
    ).getLunar()
    local_bazi = local_lunar.getEightChar()
    local_bazi.setSect(1)

    instant_lunar = Solar.fromYmdHms(
        shanghai.year, shanghai.month, shanghai.day,
        shanghai.hour, shanghai.minute, shanghai.second,
    ).getLunar()
    instant_bazi = instant_lunar.getEightChar()
    instant_bazi.setSect(1)

    previous = instant_lunar.getPrevJieQi(False)
    following = instant_lunar.getNextJieQi(False)
    if previous is None or following is None:
        raise RuntimeError("無法由曆法套件取得前後節氣")

    day_ganzhi = local_bazi.getDay()
    day_xun, _, day_void, _ = xun_for(day_ganzhi)
    term_at_shanghai = _solar_to_datetime(previous.getSolar(), shanghai_zone)
    next_at_shanghai = _solar_to_datetime(following.getSolar(), shanghai_zone)

    return CalendarContext(
        local_datetime=local,
        timezone_name=timezone_name,
        solar_term=normalize_term(previous.getName()),
        solar_term_at=term_at_shanghai.astimezone(local.tzinfo),
        next_solar_term=normalize_term(following.getName()),
        next_solar_term_at=next_at_shanghai.astimezone(local.tzinfo),
        year_ganzhi=instant_bazi.getYear(),
        month_ganzhi=instant_bazi.getMonth(),
        day_ganzhi=day_ganzhi,
        hour_ganzhi=local_bazi.getTime(),
        day_xun=day_xun,
        day_void_branches=day_void,
        tzdb_version=detect_tzdb_version(),
    )
