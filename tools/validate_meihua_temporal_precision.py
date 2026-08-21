from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
import sys
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from jarvis.meihua_timeline import build_football_temporal_audit  # noqa: E402
from meihua.engine import build_meihua_snapshot  # noqa: E402


PATH = ROOT / "knowledge" / "meihua_temporal_precision_policy.json"
FORBIDDEN_RESULT_KEYS = {
    "win_probability",
    "home_win_probability",
    "draw_probability",
    "away_win_probability",
    "fixed_score",
    "predicted_score",
    "final_result",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"Meihua temporal precision validation failed: {message}")


def _keys(value):
    if isinstance(value, dict):
        for key, child in value.items():
            yield str(key)
            yield from _keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from _keys(child)


def main() -> None:
    policy = json.loads(PATH.read_text(encoding="utf-8"))
    require(policy.get("schema_version") == "stark-meihua-temporal-precision-v1.1.0", "unexpected schema version")
    require(policy.get("anchor_rule", {}).get("name") == "ANCHOR_CAST_IMMUTABLE", "anchor cast must be immutable")
    allowed = policy.get("football_window_policy", {}).get("allowed_horizon_minutes", [])
    require(allowed == [120, 150, 180, 210], "football temporal horizons must be frozen and explicit")
    require(policy.get("football_window_policy", {}).get("default_horizon_minutes") == 180, "default football temporal horizon must be 180")
    match_clock = policy.get("match_clock_event_policy", {})
    require(match_clock.get("status") == "OPTIONAL_TIMESTAMPED_EVIDENCE", "match-clock evidence policy missing")
    require("ACTUAL_KICKOFF" in match_clock.get("allowed_event_types", []), "actual kickoff event type missing")
    require("SECOND_HALF_KICKOFF" in match_clock.get("allowed_event_types", []), "second-half event type missing")
    require(bool(match_clock.get("anti_backfill")), "match-clock anti-backfill rule missing")
    diagnostic = policy.get("diagnostic_recast_policy", {})
    require(diagnostic.get("authority") == "SECONDARY_DIAGNOSTIC_ONLY", "diagnostic recast must remain secondary")
    require("跨時辰=必然逆轉" in diagnostic.get("forbidden", []), "automatic reversal shortcut must be forbidden")
    require(bool(policy.get("classical_boundary")), "classical boundary must be explicit")
    require(bool(policy.get("source_ids")), "source ids must be present")

    anchor = datetime(2026, 6, 15, 22, 50, tzinfo=ZoneInfo("Asia/Taipei"))
    snapshot = build_meihua_snapshot(anchor, "Asia/Taipei")
    audit = build_football_temporal_audit(snapshot, horizon_minutes=180)
    require(audit.get("kind") == "meihua_football_temporal_audit", "runtime audit kind mismatch")
    require(audit.get("status") == "TEMPORAL_BOUNDARY_AUDIT_READY", "runtime audit status mismatch")
    require(audit["anchor_cast"]["hour_branch"] == "亥", "anchor hour branch mismatch")
    require(audit["match_clock_audit"]["status"] == "NOT_PROVIDED", "default match-clock status must be not provided")
    require(audit["boundary_summary"]["hour_branch_changes"] >= 2, "180-minute example must expose at least two hour-branch changes")
    require(audit["boundary_summary"]["crosses_calendar_boundary"] is True, "cross-midnight example must expose calendar boundary")

    hour_changes = [row for row in audit["boundaries"] if "HOUR_BRANCH_CHANGE" in row["boundary_types"]]
    require(hour_changes[0]["to"]["hour_branch"] == "子", "22:50 example should reach 子 at first hour boundary")
    require(hour_changes[0]["elapsed_real_minutes_from_kickoff"] == 10.0, "first hour boundary elapsed time mismatch")
    require(hour_changes[0]["diagnostic_recast"]["authority"] == "SECONDARY_DIAGNOSTIC_ONLY", "probe authority changed")
    require(hour_changes[0]["match_clock_alignment"]["status"] == "MATCH_CLOCK_EVENTS_NOT_PROVIDED", "missing match-clock status drift")

    timestamped = build_football_temporal_audit(
        snapshot,
        horizon_minutes=180,
        match_clock_events=[
            {"type": "ACTUAL_KICKOFF", "local_datetime": anchor.isoformat(), "source": "official"},
            {"type": "FIRST_HALF_END", "local_datetime": "2026-06-15T23:40:00+08:00", "match_clock_label": "HT", "source": "official"},
            {"type": "SECOND_HALF_KICKOFF", "local_datetime": "2026-06-15T23:55:00+08:00", "source": "official"},
            {"type": "REGULATION_END", "local_datetime": "2026-06-16T00:45:00+08:00", "match_clock_label": "FT", "source": "official"}
        ],
    )
    require(timestamped["match_clock_audit"]["status"] == "TIMESTAMPED_EVENTS_AVAILABLE", "timestamped events not activated")
    require(timestamped["match_clock_audit"]["event_count"] == 4, "timestamped event count mismatch")
    first_boundary = timestamped["boundaries"][0]
    require(first_boundary["match_clock_alignment"]["status"] == "TIMESTAMPED_MATCH_CLOCK_CONTEXT_AVAILABLE", "boundary not aligned to match-clock context")
    require(first_boundary["match_clock_alignment"]["phase"] == "FIRST_HALF_VERIFIED_WINDOW", "first boundary should be inside verified first-half window")

    present_keys = set(_keys(timestamped))
    require(not (present_keys & FORBIDDEN_RESULT_KEYS), f"temporal audit contains forbidden automatic result fields: {sorted(present_keys & FORBIDDEN_RESULT_KEYS)}")

    print(
        "Meihua temporal precision audit passed: immutable anchor / UTC-monotonic boundary scan / "
        "timestamped match-clock alignment / secondary diagnostic recasts / no automatic reversal"
    )


if __name__ == "__main__":
    main()
