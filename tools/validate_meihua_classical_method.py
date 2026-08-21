from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
import sys
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from jarvis.meihua_method import build_meihua_classical_method_audit  # noqa: E402
from meihua.engine import (  # noqa: E402
    LEAP_MONTH_POLICY,
    LUNAR_DAY_BOUNDARY_POLICY,
    build_meihua_snapshot_from_numbers,
)


PATH = ROOT / "knowledge" / "meihua_classical_method_audit.json"
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
        raise SystemExit(f"Meihua classical method validation failed: {message}")


def _keys(value):
    if isinstance(value, dict):
        for key, child in value.items():
            yield str(key)
            yield from _keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from _keys(child)


def main() -> None:
    payload = json.loads(PATH.read_text(encoding="utf-8"))
    require(
        payload.get("schema_version") == "stark-meihua-classical-method-audit-v1.1.0",
        "unexpected schema version",
    )
    profiles = payload.get("method_profiles", {})
    require(set(profiles) == {"XIANTIAN_NUMBER_METHOD", "HOUTIAN_OBJECT_METHOD"}, "method profiles must cover xiantian/houtian")

    xiantian = profiles["XIANTIAN_NUMBER_METHOD"]
    houtian = profiles["HOUTIAN_OBJECT_METHOD"]
    require(xiantian.get("zhouyi_role") == "SUPPORTING", "xiantian number method must keep Zhouyi text supporting")
    require(houtian.get("zhouyi_role") == "PRIMARY_SUPPORT", "houtian object method must retain primary-support text role")
    require("年月日時起卦" in xiantian.get("implemented_methods", []), "current year-month-day-hour method must be implemented")
    require(not houtian.get("implemented_methods"), "houtian object method must remain knowledge-only until engine exists")

    principles = payload.get("core_classical_principles", [])
    ids = [row.get("id") for row in principles]
    require(len(principles) >= 8, "classical principle audit is too shallow")
    require(len(ids) == len(set(ids)), "classical principle ids must be unique")
    required_principles = {
        "body_one_uses_many",
        "use_mutual_change_sequence",
        "strength_modulates_relation",
        "true_generation_true_control",
        "three_essentials_ten_responses",
        "movement_stillness",
        "inside_outside",
        "timing_is_conditional",
    }
    require(required_principles <= set(ids), "core classical principles are incomplete")
    for row in principles:
        require(bool(row.get("project_summary")), f"principle {row.get('id')} missing summary")
        require(bool(row.get("audit_requirement")), f"principle {row.get('id')} missing audit requirement")

    current = payload.get("current_engine_contract", {})
    require(current.get("engine_version") == "jarvis-meihua-year-month-day-hour-v0.3.0", "current engine version mismatch")
    require(current.get("method") == "年月日時起卦", "current method contract mismatch")
    require(current.get("method_class") == "XIANTIAN_NUMBER_METHOD", "current method must be classified as xiantian number method")
    require(current.get("zhouyi_role") == "SUPPORTING", "current engine must not promote Zhouyi line text above Meihua structure")
    require(current.get("leap_month_policy") == LEAP_MONTH_POLICY, "leap-month policy must be explicit and synchronized")
    require(
        current.get("lunar_day_boundary_policy") == LUNAR_DAY_BOUNDARY_POLICY,
        "lunar day-boundary policy must be explicit and synchronized",
    )
    require(current.get("external_response_status") == "NOT_RECORDED_BY_CURRENT_UI", "external-response gap must be explicit")
    require(bool(current.get("unimplemented_classical_layers")), "unimplemented classical layers must stay visible")

    snapshot = build_meihua_snapshot_from_numbers(
        event_local_at=datetime(2026, 6, 15, 12, 0, tzinfo=ZoneInfo("America/New_York")),
        timezone_name="America/New_York",
        year_branch="午",
        lunar_month=5,
        lunar_day=1,
        hour_branch="午",
    )
    audit = build_meihua_classical_method_audit(snapshot)
    require(audit.get("kind") == "meihua_classical_method_audit", "runtime audit kind mismatch")
    require(audit.get("status") == "METHOD_AWARE_REVIEW_READY", "runtime audit not ready")
    require(audit["method"]["class"] == "XIANTIAN_NUMBER_METHOD", "runtime method class mismatch")
    require(audit["weighting_decision"]["zhouyi_role"] == "SUPPORTING", "runtime Zhouyi role mismatch")
    layers = audit["body_use_network"]["layers"]
    require([row["layer"] for row in layers] == ["original_use", "mutual_upper", "mutual_lower", "changed_use"], "body/use network must expose four action layers")
    mutual_identities = {row.get("classical_identity") for row in layers if row["layer"].startswith("mutual_")}
    require(mutual_identities == {"body_mutual", "use_mutual"}, "mutual layers must expose body_mutual/use_mutual identities")
    require(audit["external_response_audit"]["three_essentials"] == "NOT_RECORDED", "three essentials missing-state must be explicit")
    require(audit["external_response_audit"]["ten_responses"] == "NOT_RECORDED", "ten responses missing-state must be explicit")

    present_keys = set(_keys(audit))
    require(not (present_keys & FORBIDDEN_RESULT_KEYS), f"method audit contains forbidden automatic result fields: {sorted(present_keys & FORBIDDEN_RESULT_KEYS)}")

    print(
        "Meihua classical method audit passed: xiantian/houtian separated / time conventions versioned / "
        "Zhouyi supporting / body-mutual-use-mutual network / external-response gaps explicit"
    )


if __name__ == "__main__":
    main()
