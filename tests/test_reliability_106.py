from copy import deepcopy
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from jarvis.case_bundle import build_divination_case_bundle, audit_case_collision_group
from jarvis.divination_packet import build_qimen_packet, build_meihua_packet
from jarvis.event_layers import build_differentiation_audit, _validate_ganzhi
from jarvis.provenance import sha256_payload
from jarvis.time import aware_event_local_datetime, event_zone, tzdb_version
from jarvis.validation import validate_bundle, validate_packet, load_json_object
from jarvis.workspace_state import activate_bundle, activate_packet, active_artifact
from jarvis.yuanling_packet import build_yuanling_yanshu_packet


def resign(value, key="packet_sha256"):
    value.pop(key, None)
    value[key] = sha256_payload(value)
    return value


@pytest.fixture(scope="module")
def packets():
    at = datetime(2026, 8, 22, 15, tzinfo=ZoneInfo("Europe/London"))
    args = dict(question="測試", event_at=at, timezone_name="Europe/London",
                category="football_match", home_team="A隊", away_team="B隊")
    return build_qimen_packet(**args), build_meihua_packet(**args)


def test_false_alignment_with_stale_match_identity_is_rejected(packets):
    q, m = deepcopy(packets)
    m["event"]["datetime"] = "2026-08-22T17:00:00+01:00"
    resign(m)
    with pytest.raises(ValueError, match="MISMATCH"):
        build_divination_case_bundle(q, m)


def test_outer_rehash_does_not_hide_invalid_nested_packet(packets):
    bundle = build_divination_case_bundle(*packets)
    bundle["qimen_packet"] = deepcopy(bundle["qimen_packet"])
    bundle["qimen_packet"]["question"]["text"] = "stale nested SHA"
    resign(bundle, "bundle_sha256")
    assert audit_case_collision_group([bundle])["status"] == "FAIL_INVALID_BUNDLE"


def test_optional_yuanling_does_not_split_shared_time_group(packets):
    q, m = packets
    y = build_yuanling_yanshu_packet(question="測試", event_at=datetime.fromisoformat(q["event"]["datetime"]),
                                   timezone_name=q["event"]["timezone"])
    plain = build_divination_case_bundle(q, m)
    extended = build_divination_case_bundle(q, m, yuanling_packet=y)
    audit = audit_case_collision_group([plain, extended])
    assert audit["status"] == "REVIEW_UNSAFE_COLLISION"
    assert audit["temporal_group_count"] == 1
    assert {g["system"] for g in audit["layer_groups"]} == {"qimen", "meihua"}


def test_legacy_bundle_is_validated_without_rewriting(packets):
    q, m = packets
    old = build_divination_case_bundle(q, m)
    old["schema_version"] = "DIVINATION_CASE_BUNDLE_V2"
    old["differentiation_audit"] = build_differentiation_audit(q, m, legacy=True)
    resign(old, "bundle_sha256")
    before = deepcopy(old)
    validate_bundle(old)
    assert old == before
    assert audit_case_collision_group([old, build_divination_case_bundle(q, m)])["temporal_group_count"] == 1


def test_new_packet_becomes_active_after_old_bundle(packets):
    state = {}
    activate_bundle(state, build_divination_case_bundle(*packets))
    activate_packet(state, packets[0])
    assert active_artifact(state) == ("packet", packets[0])
    assert state["stark_case_bundle"]


def test_stale_active_digest_and_ambiguous_legacy_session_fail(packets):
    state = {}
    activate_packet(state, packets[0])
    state["stark_packet"] = packets[1]
    with pytest.raises(ValueError, match="變更"):
        active_artifact(state)
    with pytest.raises(ValueError, match="多份"):
        active_artifact({"stark_case_bundle": build_divination_case_bundle(*packets), "stark_packet": packets[0]})


@pytest.mark.parametrize("raw", [b"null", b"[]", b'{"a":1,"a":2}', b'{"n":NaN}'])
def test_malformed_json_is_a_user_error(raw):
    with pytest.raises(ValueError):
        load_json_object(raw)


@pytest.mark.parametrize("value", [None, [], {"schema_version": "DIVINATION_PACKET_V2"}])
def test_incomplete_packet_rejected_by_runtime_schema(value):
    with pytest.raises(ValueError):
        validate_packet(value)


def test_aware_gap_rejected_and_pinned_fold_preserved():
    zone = "America/New_York"
    gap = datetime(2026, 3, 8, 2, 30, tzinfo=ZoneInfo(zone))
    with pytest.raises(ValueError, match="不存在"):
        aware_event_local_datetime(gap, zone)
    first = aware_event_local_datetime(datetime(2026, 11, 1, 1, 30), zone, fold=0)
    second = aware_event_local_datetime(datetime(2026, 11, 1, 1, 30), zone, fold=1)
    assert second.timestamp() - first.timestamp() == 3600
    assert first.tzinfo is event_zone(zone)
    assert "iana-" in tzdb_version()


@pytest.mark.parametrize("value", ["甲丑", "乙子", "2020", None])
def test_invalid_birth_year_ganzhi_is_rejected(value):
    with pytest.raises(ValueError):
        _validate_ganzhi(value, "出生年干支")
