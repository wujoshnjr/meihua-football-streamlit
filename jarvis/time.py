from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


class EventLocalTimeError(ValueError):
    pass


def _zone(timezone_name: str) -> ZoneInfo:
    try:
        return ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise EventLocalTimeError(f"找不到 IANA 時區：{timezone_name}") from exc


def inspect_local_civil_time(value: datetime, timezone_name: str) -> dict[str, object]:
    """Inspect a naive local civil datetime before it becomes an event instant.

    The result distinguishes normal, ambiguous (DST fall-back) and nonexistent
    (DST spring-forward) wall times. It never silently chooses between two real
    instants when the wall clock is ambiguous.
    """

    if value.tzinfo is not None:
        raise EventLocalTimeError("inspect_local_civil_time 只接受 naive local datetime")

    zone = _zone(timezone_name)
    utc = ZoneInfo("UTC")
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
        return value.astimezone(zone)
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
    roundtrip = candidate.astimezone(ZoneInfo("UTC")).astimezone(zone)
    if roundtrip.replace(tzinfo=None) != value:
        raise EventLocalTimeError(f"{value.isoformat()} 在 {timezone_name} 是不存在的夏令時間")
    return candidate
