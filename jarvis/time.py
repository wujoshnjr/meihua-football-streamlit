from __future__ import annotations

from datetime import datetime, timezone
from functools import lru_cache
from importlib import resources
from zoneinfo import ZoneInfo

EVENT_TIME_POLICY_VERSION = "PINNED_TZDATA_V1"


class EventLocalTimeError(ValueError):
    pass


@lru_cache(maxsize=256)
def event_zone(timezone_name: str) -> ZoneInfo:
    """Read the pinned wheel directly, independently of OS TZPATH and caches."""
    if not isinstance(timezone_name, str) or not timezone_name or any(
        part in {"", ".", ".."} for part in timezone_name.split("/")
    ) or "\\" in timezone_name:
        raise EventLocalTimeError("請提供有效 IANA 時區")
    try:
        source = resources.files("tzdata.zoneinfo").joinpath(*timezone_name.split("/"))
        with source.open("rb") as handle:
            return ZoneInfo.from_file(handle, key=timezone_name)
    except (OSError, ValueError, ModuleNotFoundError) as exc:
        raise EventLocalTimeError(f"找不到 IANA 時區：{timezone_name}") from exc


def tzdb_version() -> str:
    import tzdata

    return f"tzdata-wheel-{tzdata.__version__};iana-{tzdata.IANA_VERSION}"


_zone = event_zone


def inspect_local_civil_time(value: datetime, timezone_name: str) -> dict[str, object]:
    """Inspect a naive local civil datetime before it becomes an event instant.

    The result distinguishes normal, ambiguous (DST fall-back) and nonexistent
    (DST spring-forward) wall times. It never silently chooses between two real
    instants when the wall clock is ambiguous.
    """

    if value.tzinfo is not None:
        raise EventLocalTimeError("inspect_local_civil_time 只接受 naive local datetime")

    zone = _zone(timezone_name)
    utc = timezone.utc
    candidates: list[dict[str, object]] = []
    for fold in (0, 1):
        candidate = value.replace(tzinfo=zone, fold=fold)
        roundtrip = candidate.astimezone(utc).astimezone(zone)
        exists = roundtrip.replace(tzinfo=None) == value
        candidates.append(
            {
                "fold": fold,
                "exists": exists,
                "local_datetime": candidate.isoformat(),
                "utc_datetime": candidate.astimezone(utc).isoformat(),
                "utc_offset_seconds": int(candidate.utcoffset().total_seconds()) if candidate.utcoffset() else 0,
            }
        )

    valid = [row for row in candidates if row["exists"]]
    nonexistent = not valid
    ambiguous = (
        len(valid) == 2
        and valid[0]["utc_offset_seconds"] != valid[1]["utc_offset_seconds"]
        and valid[0]["utc_datetime"] != valid[1]["utc_datetime"]
    )
    status = "NONEXISTENT" if nonexistent else "AMBIGUOUS" if ambiguous else "UNAMBIGUOUS"
    return {
        "status": status,
        "timezone": timezone_name,
        "wall_datetime": value.isoformat(),
        "ambiguous": ambiguous,
        "nonexistent": nonexistent,
        "candidates": valid if valid else candidates,
        "rule": "AMBIGUOUS 時刻必須明確選 fold=0 或 fold=1；NONEXISTENT 時刻不得自動位移。",
    }


def aware_event_local_datetime(
    value: datetime,
    timezone_name: str,
    *,
    fold: int = 0,
    reject_ambiguous_without_explicit_fold: bool = False,
) -> datetime:
    """Return a validated event-location civil datetime.

    A naive datetime is interpreted in ``timezone_name``. Aware values are
    converted into that zone. Non-existent DST wall times are rejected rather
    than silently attaching an invalid offset. Callers that cannot tolerate an
    ambiguous repeated wall time can set ``reject_ambiguous_without_explicit_fold``
    and then prompt the user to choose fold 0 or 1 explicitly.
    """

    zone = _zone(timezone_name)
    if value.tzinfo is not None:
        # A ZoneInfo-aware datetime can still have been constructed in a gap.
        roundtrip = value.astimezone(timezone.utc).astimezone(value.tzinfo)
        if (roundtrip.replace(tzinfo=None), roundtrip.utcoffset()) != (
            value.replace(tzinfo=None), value.utcoffset()
        ):
            raise EventLocalTimeError(f"{value.isoformat()} 是不存在或不一致的事件時間")
        return value.astimezone(timezone.utc).astimezone(zone)
    if fold not in (0, 1):
        raise EventLocalTimeError("fold 必須是 0 或 1")

    audit = inspect_local_civil_time(value, timezone_name)
    if audit["nonexistent"]:
        raise EventLocalTimeError(f"{value.isoformat()} 在 {timezone_name} 是不存在的夏令時間")
    if audit["ambiguous"] and reject_ambiguous_without_explicit_fold:
        raise EventLocalTimeError(
            f"{value.isoformat()} 在 {timezone_name} 是 DST 回撥造成的重複時間；請明確選擇 fold=0 或 fold=1"
        )

    candidate = value.replace(tzinfo=zone, fold=fold)
    roundtrip = candidate.astimezone(timezone.utc).astimezone(zone)
    if roundtrip.replace(tzinfo=None) != value:
        raise EventLocalTimeError(f"{value.isoformat()} 在 {timezone_name} 是不存在的夏令時間")
    return candidate
