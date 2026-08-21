from datetime import datetime
from zoneinfo import ZoneInfo

from jarvis.meihua_method import build_meihua_classical_method_audit
from meihua import build_meihua_snapshot_from_numbers


def _snapshot(hour_branch: str):
    return build_meihua_snapshot_from_numbers(
        event_local_at=datetime(2026, 1, 1, 8, 0, tzinfo=ZoneInfo("Asia/Taipei")),
        timezone_name="Asia/Taipei",
        year_branch="午",
        lunar_month=5,
        lunar_day=12,
        hour_branch=hour_branch,
    )


def test_body_in_upper_maps_upper_mutual_to_body_mutual():
    snapshot = _snapshot("子")
    assert snapshot.moving_line <= 3
    audit = build_meihua_classical_method_audit(snapshot)
    network = audit["body_use_network"]
    identities = {row["source_position"]: row["classical_identity"] for row in network["layers"]}

    assert network["body_position"] == "upper"
    assert identities["upper"] == "body_mutual"
    assert identities["lower"] == "use_mutual"
    assert network["body_mutual_source_position"] == "upper"


def test_body_in_lower_maps_lower_mutual_to_body_mutual():
    snapshot = _snapshot("辰")
    assert snapshot.moving_line > 3
    audit = build_meihua_classical_method_audit(snapshot)
    network = audit["body_use_network"]
    identities = {row["source_position"]: row["classical_identity"] for row in network["layers"]}

    assert network["body_position"] == "lower"
    assert identities["lower"] == "body_mutual"
    assert identities["upper"] == "use_mutual"
    assert network["body_mutual_source_position"] == "lower"
