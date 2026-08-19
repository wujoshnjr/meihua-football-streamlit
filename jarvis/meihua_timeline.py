from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from meihua.engine import MeihuaSnapshot, build_meihua_snapshot


ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "knowledge" / "meihua_temporal_precision_policy.json"


@lru_cache(maxsize=1)
def _policy() -> dict[str, Any]:
    if not POLICY_PATH.exists():
        raise RuntimeError("缺少 knowledge/meihua_temporal_precision_policy.json")
    return json.loads(POLICY_PATH.read_text(encoding="utf-8"))


def meihua_temporal_precision_policy() -> dict[str, Any]:
    return _policy()


def _lunar_context(instant_utc: datetime, timezone_name: str) -> dict[str, Any]:
    local = instant_utc.astimezone(ZoneInfo(timezone_name))
    try:
        from lunar_python import Solar
    except ImportError as exc:
        raise RuntimeError("缺少 lunar_python==1.4.8") from exc
    lunar = Solar.fromYmdHms(
        local.year,
        local.month,
        local.day,
        local.hour,
        local.minute,
        local.second,
    ).getLunar()
    return {
        "local_datetime": local,
        "civil_date": local.date().isoformat(),
        "utc_offset_seconds": int((local.utcoffset() or timedelta()).total_seconds()),
        "lunar_year": int(lunar.getYear()),
        "lunar_month": int(lunar.getMonth()),
        "lunar_day": int(lunar.getDay()),
        "hour_branch": str(lunar.getTimeZhi()),
    }


def _snapshot_core(snapshot: MeihuaSnapshot) -> dict[str, Any]:
    return {
        "upper_trigram": snapshot.upper_trigram,
        "lower_trigram": snapshot.lower_trigram,
        "moving_line": snapshot.moving_line,
        "body_trigram": snapshot.body_trigram,
        "use_trigram": snapshot.use_trigram,
        "body_use_relation": snapshot.body_use_relation,
        "mutual_upper_trigram": snapshot.mutual_upper_trigram,
        "mutual_lower_trigram": snapshot.mutual_lower_trigram,
        "changed_upper_trigram": snapshot.changed_upper_trigram,
        "changed_lower_trigram": snapshot.changed_lower_trigram,
        "changed_use_trigram": snapshot.changed_use_trigram,
        "changed_use_relation_to_body": snapshot.changed_use_relation_to_body,
        "body_season_state": snapshot.body_season_state,
    }


def _phase_hint(elapsed_minutes: float) -> dict[str, Any]:
    if elapsed_minutes < 45:
        phase = "FIRST_HALF_LIKELY"
        note = "以無額外中斷的 nominal wall-clock 看，較可能仍在上半場。"
    elif elapsed_minutes < 65:
        phase = "HALFTIME_OR_TRANSITION_UNCERTAIN"
        note = "可能處於上半場傷停、半場休息或下半場初段；必須用實際 match clock 核對。"
    elif elapsed_minutes < 115:
        phase = "SECOND_HALF_OR_LATE_REGULATION_LIKELY"
        note = "較可能位於下半場或正規時間末段，但傷停與延誤會改變對應。"
    else:
        phase = "LATE_OR_EXTRA_TIME_UNCERTAIN"
        note = "可能已完賽、仍在長傷停/延誤，或進入延長賽；不能只靠 wall-clock 判定。"
    return {
        "status": "PROJECT_COARSE_PHASE_HINT__REQUIRES_MATCH_CLOCK",
        "phase": phase,
        "note": note,
    }


def _diagnostic_recast(
    *,
    anchor: MeihuaSnapshot,
    boundary_utc: datetime,
    timezone_name: str,
) -> dict[str, Any]:
    probe = build_meihua_snapshot(boundary_utc, timezone_name)
    anchor_core = _snapshot_core(anchor)
    probe_core = _snapshot_core(probe)
    changed_fields = [key for key in anchor_core if anchor_core[key] != probe_core[key]]
    return {
        "status": "PROJECT_DIAGNOSTIC__NOT_PRIMARY_CLASSICAL_CAST",
        "authority": "SECONDARY_DIAGNOSTIC_ONLY",
        "local_datetime": probe.event_local_at.isoformat(),
        "hour_branch": probe.hour_branch,
        "lunar_month": probe.lunar_month,
        "lunar_day": probe.lunar_day,
        "snapshot_core": probe_core,
        "changed_fields_vs_anchor": changed_fields,
        "changed_field_count": len(changed_fields),
        "rule": "這是交界時刻若重新提出同一問題時的獨立 diagnostic snapshot；不得覆蓋開賽 anchor cast。",
    }


def build_football_temporal_audit(
    snapshot: MeihuaSnapshot,
    *,
    horizon_minutes: int = 180,
) -> dict[str, Any]:
    """Audit time boundaries across a football event without replacing the anchor cast.

    The scan advances through real UTC minutes and converts each instant back to
    the event IANA timezone. This keeps elapsed time monotonic through DST while
    exposing local hour-branch, civil-date, lunar-date and UTC-offset changes.
    """

    policy = _policy()
    allowed = set(policy["football_window_policy"]["allowed_horizon_minutes"])
    if horizon_minutes not in allowed:
        raise ValueError(f"timeline_horizon_minutes 必須是 {sorted(allowed)} 之一")

    timezone_name = snapshot.timezone_name
    anchor_local = snapshot.event_local_at
    if anchor_local.tzinfo is None:
        raise ValueError("Meihua snapshot event_local_at 必須含時區")
    start_utc = anchor_local.astimezone(timezone.utc)
    end_utc = start_utc + timedelta(minutes=horizon_minutes)

    previous = _lunar_context(start_utc, timezone_name)
    cursor = start_utc.replace(second=0, microsecond=0)
    if cursor <= start_utc:
        cursor += timedelta(minutes=1)

    boundaries: list[dict[str, Any]] = []
    while cursor <= end_utc:
        current = _lunar_context(cursor, timezone_name)
        kinds: list[str] = []
        if current["hour_branch"] != previous["hour_branch"]:
            kinds.append("HOUR_BRANCH_CHANGE")
        if current["civil_date"] != previous["civil_date"]:
            kinds.append("CIVIL_DATE_CHANGE")
        if (
            current["lunar_year"],
            current["lunar_month"],
            current["lunar_day"],
        ) != (
            previous["lunar_year"],
            previous["lunar_month"],
            previous["lunar_day"],
        ):
            kinds.append("LUNAR_DATE_CHANGE")
        if current["utc_offset_seconds"] != previous["utc_offset_seconds"]:
            kinds.append("UTC_OFFSET_CHANGE")

        if kinds:
            elapsed = (cursor - start_utc).total_seconds() / 60.0
            boundaries.append(
                {
                    "boundary_types": kinds,
                    "utc_datetime": cursor.isoformat(),
                    "local_datetime": current["local_datetime"].isoformat(),
                    "elapsed_real_minutes_from_kickoff": round(elapsed, 3),
                    "from": {
                        "civil_date": previous["civil_date"],
                        "lunar_year": previous["lunar_year"],
                        "lunar_month": previous["lunar_month"],
                        "lunar_day": previous["lunar_day"],
                        "hour_branch": previous["hour_branch"],
                        "utc_offset_seconds": previous["utc_offset_seconds"],
                    },
                    "to": {
                        "civil_date": current["civil_date"],
                        "lunar_year": current["lunar_year"],
                        "lunar_month": current["lunar_month"],
                        "lunar_day": current["lunar_day"],
                        "hour_branch": current["hour_branch"],
                        "utc_offset_seconds": current["utc_offset_seconds"],
                    },
                    "football_phase_hint": _phase_hint(elapsed),
                    "diagnostic_recast": _diagnostic_recast(
                        anchor=snapshot,
                        boundary_utc=cursor,
                        timezone_name=timezone_name,
                    ),
                }
            )
        previous = current
        cursor += timedelta(minutes=1)

    hour_branch_changes = [row for row in boundaries if "HOUR_BRANCH_CHANGE" in row["boundary_types"]]
    calendar_changes = [
        row
        for row in boundaries
        if {"CIVIL_DATE_CHANGE", "LUNAR_DATE_CHANGE"} & set(row["boundary_types"])
    ]
    offset_changes = [row for row in boundaries if "UTC_OFFSET_CHANGE" in row["boundary_types"]]

    return {
        "kind": "meihua_football_temporal_audit",
        "schema_version": policy["schema_version"],
        "status": "TEMPORAL_BOUNDARY_AUDIT_READY",
        "anchor_cast": {
            "local_datetime": anchor_local.isoformat(),
            "hour_branch": snapshot.hour_branch,
            "lunar_month": snapshot.lunar_month,
            "lunar_day": snapshot.lunar_day,
            "rule": policy["anchor_rule"]["rule"],
        },
        "analysis_window": {
            "horizon_minutes": horizon_minutes,
            "start_local": anchor_local.isoformat(),
            "end_local": end_utc.astimezone(ZoneInfo(timezone_name)).isoformat(),
            "meaning": policy["football_window_policy"]["meaning"],
            "clock_rule": policy["football_window_policy"]["clock_rule"],
        },
        "boundary_summary": {
            "total_boundary_events": len(boundaries),
            "hour_branch_changes": len(hour_branch_changes),
            "calendar_changes": len(calendar_changes),
            "utc_offset_changes": len(offset_changes),
            "crosses_hour_branch": bool(hour_branch_changes),
            "crosses_calendar_boundary": bool(calendar_changes),
            "crosses_utc_offset": bool(offset_changes),
        },
        "boundaries": boundaries,
        "interpretation_contract": list(policy["ai_review_order"]),
        "diagnostic_recast_policy": policy["diagnostic_recast_policy"],
        "classical_boundary": list(policy["classical_boundary"]),
        "source_ids": list(policy["source_ids"]),
        "boundary": (
            "此時間層精確找出事件期間的時支/日界/DST輸入變化；"
            "它不把『跨時辰』等同『必然逆轉』，也不把 diagnostic recast 變成新的主卦。"
        ),
    }
