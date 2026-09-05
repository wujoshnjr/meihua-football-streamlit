from __future__ import annotations

from datetime import datetime
from typing import Any

from jarvis.provenance import sha256_payload
from jarvis.event_layers import audit_case_collision, build_differentiation_audit
from jarvis.validation import validate_bundle, validate_packet

MATCH_EVENT_VERSION = "MATCH_EVENT_V1"
DIVINATION_CASE_BUNDLE_VERSION = "DIVINATION_CASE_BUNDLE_V3"
FOOTBALL_COLLISION_GROUP_AUDIT_VERSION = "FOOTBALL_COLLISION_GROUP_AUDIT_V2"


def _clean_team(value: str, field: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field} 不可空白")
    return cleaned


def build_match_event_identity(
    *,
    home_team: str,
    away_team: str,
    event_datetime: datetime,
    timezone_name: str,
) -> dict[str, Any]:
    """Build the deterministic same-event identity shared by Qimen and Meihua."""

    if event_datetime.tzinfo is None:
        raise ValueError("event_datetime 必須含時區")
    timezone = timezone_name.strip()
    if not timezone:
        raise ValueError("timezone_name 不可空白")
    payload: dict[str, Any] = {
        "schema_version": MATCH_EVENT_VERSION,
        "category": "football_match",
        "home_team": _clean_team(home_team, "home_team"),
        "away_team": _clean_team(away_team, "away_team"),
        "event_datetime": event_datetime.isoformat(),
        "timezone": timezone,
        "identity_rule": "HOME_AWAY_EVENT_LOCAL_DATETIME_TIMEZONE",
    }
    payload["match_event_sha256"] = sha256_payload(payload)
    return payload


def verify_packet_integrity(packet: dict[str, Any]) -> dict[str, Any]:
    """Verify the deterministic packet SHA before import or cross-system join."""

    if not isinstance(packet, dict):
        return {"status": "FAIL", "reason": "PACKET_OBJECT_REQUIRED", "expected": None, "actual": None}
    expected = str(packet.get("packet_sha256", ""))
    if not expected:
        return {"status": "FAIL", "reason": "PACKET_SHA_MISSING", "expected": None, "actual": None}
    copy = dict(packet)
    copy.pop("packet_sha256", None)
    actual = sha256_payload(copy)
    return {
        "status": "PASS" if actual == expected else "FAIL",
        "reason": "MATCH" if actual == expected else "PACKET_SHA_MISMATCH",
        "expected": expected,
        "actual": actual,
    }


def verify_bundle_integrity(bundle: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(bundle, dict):
        return {"status": "FAIL", "reason": "BUNDLE_OBJECT_REQUIRED", "expected": None, "actual": None}
    expected = str(bundle.get("bundle_sha256", ""))
    if not expected:
        return {"status": "FAIL", "reason": "BUNDLE_SHA_MISSING", "expected": None, "actual": None}
    copy = dict(bundle)
    copy.pop("bundle_sha256", None)
    actual = sha256_payload(copy)
    return {
        "status": "PASS" if actual == expected else "FAIL",
        "reason": "MATCH" if actual == expected else "BUNDLE_SHA_MISMATCH",
        "expected": expected,
        "actual": actual,
    }


def audit_case_collision_group(
    bundles: list[dict[str, Any]],
) -> dict[str, Any]:
    """Audit a kickoff cohort for temporal collisions without interpretation."""

    if not bundles:
        raise ValueError("collision group 至少需要 1 份 Case Bundle")
    if len(bundles) > 50:
        raise ValueError("collision group 一次最多 50 份 Case Bundle")

    rows: list[dict[str, Any]] = []
    invalid: list[dict[str, Any]] = []
    for index, bundle in enumerate(bundles):
        if not isinstance(bundle, dict):
            invalid.append({"input_index": index, "reason": "BUNDLE_OBJECT_REQUIRED", "schema_version": None})
            continue
        integrity = verify_bundle_integrity(bundle)
        normalized_audit = None
        if integrity["status"] == "PASS":
            try:
                validate_bundle(bundle)
                normalized_audit = build_differentiation_audit(
                    bundle["qimen_packet"], bundle["meihua_packet"], bundle.get("yuanling_packet")
                )
            except (ValueError, KeyError, TypeError, AttributeError) as exc:
                invalid.append({"input_index": index, "reason": str(exc), "schema_version": bundle.get("schema_version")})
        row = {
            "input_index": index,
            "schema_version": bundle.get("schema_version"),
            "bundle_sha256": bundle.get("bundle_sha256"),
            "integrity": integrity,
            "match_event": bundle.get("match_event"),
            "differentiation_audit": normalized_audit,
        }
        rows.append(row)
        if bundle.get("schema_version") not in {"DIVINATION_CASE_BUNDLE_V2", DIVINATION_CASE_BUNDLE_VERSION}:
            invalid.append(
                {
                    "input_index": index,
                    "reason": "UNSUPPORTED_CASE_BUNDLE_VERSION",
                    "schema_version": bundle.get("schema_version"),
                }
            )
        if integrity["status"] != "PASS":
            invalid.append(
                {
                    "input_index": index,
                    "reason": integrity["reason"],
                    "schema_version": bundle.get("schema_version"),
                }
            )

    if invalid:
        payload: dict[str, Any] = {
            "schema_version": FOOTBALL_COLLISION_GROUP_AUDIT_VERSION,
            "status": "FAIL_INVALID_BUNDLE",
            "bundle_count": len(bundles),
            "invalid": invalid,
            "groups": [],
            "rule": (
                "批次 collision audit 只接受 SHA integrity PASS 的 DIVINATION_CASE_BUNDLE_V2。"
            ),
        }
        payload["group_audit_sha256"] = sha256_payload(payload)
        return payload

    rows.sort(key=lambda row: str(row["bundle_sha256"]))
    grouped: dict[str, list[dict[str, Any]]] = {}
    missing_temporal: list[str] = []
    for row in rows:
        audit = row["differentiation_audit"] or {}
        temporal = (audit.get("temporal") or {}).get("temporal_signature_sha256")
        if not temporal:
            missing_temporal.append(str(row["bundle_sha256"]))
            continue
        grouped.setdefault(str(temporal), []).append(row)

    if missing_temporal:
        payload = {
            "schema_version": FOOTBALL_COLLISION_GROUP_AUDIT_VERSION,
            "status": "FAIL_TEMPORAL_SIGNATURE_MISSING",
            "bundle_count": len(bundles),
            "missing_temporal_bundle_sha256": sorted(missing_temporal),
            "groups": [],
            "rule": "缺少 temporal signature 的案件不得進入跨 fixture collision 判讀。",
        }
        payload["group_audit_sha256"] = sha256_payload(payload)
        return payload

    groups: list[dict[str, Any]] = []
    unsafe_count = 0
    collision_count = 0
    cross_fixture_collision_count = 0
    for temporal_signature in sorted(grouped):
        group_rows = grouped[temporal_signature]
        event_signatures = [
            ((row["differentiation_audit"] or {}).get("event") or {}).get(
                "event_signature_sha256"
            )
            for row in group_rows
        ]
        ready_event_signatures = [sig for sig in event_signatures if sig]
        unique_event_signatures = sorted(set(ready_event_signatures))
        same_temporal_collision = len(group_rows) > 1
        if same_temporal_collision:
            collision_count += 1

        if not same_temporal_collision:
            status = "NO_TEMPORAL_COLLISION"
        elif len(ready_event_signatures) != len(group_rows):
            status = "UNSAFE_TEMPORAL_COLLISION__EVENT_IDENTITY_MISSING"
            unsafe_count += 1
        elif len(unique_event_signatures) == 1:
            status = "SAME_TEMPORAL_AND_EVENT_IDENTITY"
        else:
            status = "TEMPORAL_COLLISION__DISTINGUISHED_BY_EVENT_LAYER"
            cross_fixture_collision_count += 1

        pairwise: list[dict[str, Any]] = []
        for left_index in range(len(group_rows)):
            for right_index in range(left_index + 1, len(group_rows)):
                left = group_rows[left_index]
                right = group_rows[right_index]
                pairwise.append(
                    {
                        "left_bundle_sha256": left["bundle_sha256"],
                        "right_bundle_sha256": right["bundle_sha256"],
                        "audit": audit_case_collision(
                            bundles[left["input_index"]],
                            bundles[right["input_index"]],
                            _validated=True,
                        ),
                    }
                )

        groups.append(
            {
                "temporal_signature_sha256": temporal_signature,
                "bundle_count": len(group_rows),
                "status": status,
                "event_signature_count": len(unique_event_signatures),
                "missing_event_identity_count": len(group_rows)
                - len(ready_event_signatures),
                "bundles": [
                    {
                        "bundle_sha256": row["bundle_sha256"],
                        "match_event": row["match_event"],
                        "event_signature_sha256": (
                            ((row["differentiation_audit"] or {}).get("event") or {}).get(
                                "event_signature_sha256"
                            )
                        ),
                        "participant_status": (
                            ((row["differentiation_audit"] or {}).get("participant") or {}).get(
                                "status"
                            )
                        ),
                    }
                    for row in group_rows
                ],
                "pairwise": pairwise,
            }
        )

    layer_groups = []
    for system in ("qimen", "meihua", "yuanling"):
        layers: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            signature = row["differentiation_audit"]["temporal"]["layer_signatures"].get(system)
            if signature:
                layers.setdefault(signature, []).append(row)
        for signature, members in sorted(layers.items()):
            if len(members) < 2:
                continue
            events = [r["differentiation_audit"]["event"]["event_signature_sha256"] for r in members]
            if any(not event for event in events):
                layer_status = "UNSAFE_TEMPORAL_COLLISION__EVENT_IDENTITY_MISSING"
            elif len(set(events)) == 1:
                layer_status = "SAME_TEMPORAL_AND_EVENT_IDENTITY"
            else:
                layer_status = "TEMPORAL_COLLISION__DISTINGUISHED_BY_EVENT_LAYER"
            layer_groups.append({"system": system, "signature_sha256": signature,
                                 "bundle_count": len(members), "status": layer_status,
                                 "bundle_sha256s": [r["bundle_sha256"] for r in members]})
    layer_unsafe = sum(g["status"].startswith("UNSAFE_") for g in layer_groups)
    status = "REVIEW_UNSAFE_COLLISION" if unsafe_count or layer_unsafe else "PASS"
    payload = {
        "schema_version": FOOTBALL_COLLISION_GROUP_AUDIT_VERSION,
        "status": status,
        "bundle_count": len(rows),
        "temporal_group_count": len(groups),
        "temporal_collision_group_count": collision_count,
        "cross_fixture_collision_group_count": cross_fixture_collision_count,
        "unsafe_collision_group_count": unsafe_count,
        "groups": groups,
        "layer_groups": layer_groups,
        "unsafe_layer_group_count": layer_unsafe,
        "rule": (
            "相同 temporal signature 的案件必須以賽前固定 event identity 分辨；"
            "若 event identity 缺失，批次 audit 只標 REVIEW，不允許靠 temporal interpretation 自行分叉。"
        ),
    }
    payload["group_audit_sha256"] = sha256_payload(payload)
    return payload


def _football_fixture(packet: dict[str, Any]) -> tuple[str, str]:
    fixture = packet.get("football_fixture")
    if isinstance(fixture, dict):
        return str(fixture.get("home_team", "")).strip(), str(fixture.get("away_team", "")).strip()
    host_guest = packet.get("host_guest")
    if isinstance(host_guest, dict):
        return str(host_guest.get("home_team", "")).strip(), str(host_guest.get("away_team", "")).strip()
    return "", ""


def _derive_match_event(packet: dict[str, Any]) -> dict[str, Any]:
    if packet.get("question", {}).get("category") != "football_match":
        raise ValueError("CASE_ALIGNMENT_FAIL: 只允許 football_match packet 建立雙術數 case bundle")
    home_team, away_team = _football_fixture(packet)
    event = packet.get("event") or {}
    try:
        event_datetime = datetime.fromisoformat(str(event["datetime"]))
        timezone_name = str(event["timezone"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("CASE_ALIGNMENT_FAIL: packet event identity 不完整") from exc
    return build_match_event_identity(
        home_team=home_team,
        away_team=away_team,
        event_datetime=event_datetime,
        timezone_name=timezone_name,
    )


def _clean_event_metadata(event_metadata: dict[str, Any] | None) -> dict[str, Any] | None:
    if not event_metadata:
        return None
    allowed = (
        "competition",
        "season",
        "stage",
        "stadium",
        "city",
        "country",
        "kickoff_basis",
        "time_verification_status",
        "time_source",
        "mode",
    )
    cleaned = {key: str(event_metadata.get(key, "")).strip() for key in allowed}
    cleaned = {key: value for key, value in cleaned.items() if value}
    if "mode" in cleaned and cleaned["mode"] not in {"PREMATCH", "LIVE", "HISTORICAL_BACKTEST"}:
        raise ValueError("event_metadata.mode 必須是 PREMATCH / LIVE / HISTORICAL_BACKTEST")
    return cleaned or None


def build_divination_case_bundle(
    qimen_packet: dict[str, Any],
    meihua_packet: dict[str, Any],
    *,
    yuanling_packet: dict[str, Any] | None = None,
    event_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Join Qimen/Meihua and an optional Yuanling temporal sibling for one match."""

    if not isinstance(qimen_packet, dict) or not isinstance(meihua_packet, dict):
        raise ValueError("CASE_ALIGNMENT_FAIL: packet 必須是 JSON object")
    if yuanling_packet is not None and not isinstance(yuanling_packet, dict):
        raise ValueError("CASE_ALIGNMENT_FAIL: Yuanling packet 必須是 JSON object")
    if qimen_packet.get("system") != "QIMEN_DUNJIA":
        raise ValueError("CASE_ALIGNMENT_FAIL: qimen_packet.system 必須是 QIMEN_DUNJIA")
    if meihua_packet.get("system") != "MEIHUA_YISHU":
        raise ValueError("CASE_ALIGNMENT_FAIL: meihua_packet.system 必須是 MEIHUA_YISHU")
    if yuanling_packet is not None and yuanling_packet.get("system") != "YUANLING_YANSHU_QIYAO":
        raise ValueError("CASE_ALIGNMENT_FAIL: yuanling_packet.system 必須是 YUANLING_YANSHU_QIYAO")

    qimen_integrity = verify_packet_integrity(qimen_packet)
    meihua_integrity = verify_packet_integrity(meihua_packet)
    yuanling_integrity = verify_packet_integrity(yuanling_packet) if yuanling_packet is not None else None
    if qimen_integrity["status"] != "PASS":
        raise ValueError("CASE_ALIGNMENT_FAIL: QIMEN_PACKET_SHA_INVALID")
    if meihua_integrity["status"] != "PASS":
        raise ValueError("CASE_ALIGNMENT_FAIL: MEIHUA_PACKET_SHA_INVALID")
    if yuanling_integrity is not None and yuanling_integrity["status"] != "PASS":
        raise ValueError("CASE_ALIGNMENT_FAIL: YUANLING_PACKET_SHA_INVALID")

    for packet in (qimen_packet, meihua_packet, yuanling_packet):
        if packet is not None:
            try:
                validate_packet(packet)
            except ValueError as exc:
                raise ValueError(f"CASE_ALIGNMENT_FAIL: {exc}") from exc

    qimen_event = qimen_packet.get("match_event") or _derive_match_event(qimen_packet)
    meihua_event = meihua_packet.get("match_event") or _derive_match_event(meihua_packet)
    fields = ("home_team", "away_team", "event_datetime", "timezone", "match_event_sha256")
    alignment = {
        field: {
            "qimen": qimen_event.get(field),
            "meihua": meihua_event.get(field),
            "match": qimen_event.get(field) == meihua_event.get(field),
        }
        for field in fields
    }
    mismatches = [field for field, row in alignment.items() if not row["match"]]
    if mismatches:
        raise ValueError("CASE_ALIGNMENT_FAIL: " + ", ".join(mismatches))

    yuanling_alignment = None
    if yuanling_packet is not None:
        y_event = yuanling_packet.get("event") or {}
        yuanling_alignment = {
            "datetime": {
                "qimen": qimen_packet.get("event", {}).get("datetime"),
                "yuanling": y_event.get("datetime"),
                "match": qimen_packet.get("event", {}).get("datetime") == y_event.get("datetime"),
            },
            "timezone": {
                "qimen": qimen_packet.get("event", {}).get("timezone"),
                "yuanling": y_event.get("timezone"),
                "match": qimen_packet.get("event", {}).get("timezone") == y_event.get("timezone"),
            },
        }
        y_mismatches = [field for field, row in yuanling_alignment.items() if not row["match"]]
        if y_mismatches:
            raise ValueError("CASE_ALIGNMENT_FAIL: YUANLING_" + ", ".join(y_mismatches).upper())

    differentiation_audit = build_differentiation_audit(
        qimen_packet, meihua_packet, yuanling_packet
    )

    payload: dict[str, Any] = {
        "schema_version": DIVINATION_CASE_BUNDLE_VERSION,
        "packet_purpose": "FOOTBALL_MULTI_LAYER_HANDOFF__CHATGPT_INTERPRETS",
        "match_event": qimen_event,
        "event_metadata": _clean_event_metadata(event_metadata),
        "differentiation_audit": differentiation_audit,
        "alignment_audit": {
            "status": "PASS",
            "checked_fields": list(fields),
            "fields": alignment,
            "packet_integrity": {
                "qimen": qimen_integrity,
                "meihua": meihua_integrity,
                "yuanling": yuanling_integrity,
            },
            "yuanling_temporal_alignment": yuanling_alignment,
        },
        "interpretation_roles": {
            "qimen": {
                "role": "RESULT_ENGINE_INPUT",
                "rule": "奇門是 ChatGPT 判斷正規時間勝負與候選比分的主要術數證據層；JARVIS 本身不自動輸出勝負、比分或統計機率。",
            },
            "meihua": {
                "role": "STRUCTURE_STRESS_TEST",
                "rule": "梅花負責開局／中段／後段結構、轉折條件、支持與反證；不得再獨立產生第二套勝負或比分與奇門投票。",
            },
            "yuanling": {
                "role": "TEMPORAL_NUMERIC_CONTEXT",
                "status": "INCLUDED" if yuanling_packet is not None else "NOT_INCLUDED",
                "rule": "元靈七要只作共同時段數勢／source-aware numeric context；不得直接把宮數、星數或射覆數換成比分。",
            },
            "final": {
                "role": "CHATGPT_FINAL_SYNTHESIS",
                "rule": "ChatGPT 保留矛盾與不確定性後做最終合參；不可重新起局或起卦。",
            },
        },
        "qimen_packet_sha256": qimen_packet.get("packet_sha256"),
        "meihua_packet_sha256": meihua_packet.get("packet_sha256"),
        "yuanling_packet_sha256": (
            yuanling_packet.get("packet_sha256") if yuanling_packet is not None else None
        ),
        "qimen_packet": qimen_packet,
        "meihua_packet": meihua_packet,
        "yuanling_packet": yuanling_packet,
        "ai_handoff_contract": [
            "先做 alignment_audit 與 packet_integrity；若不是 PASS，停止合參。",
            "奇門作 RESULT_ENGINE_INPUT；梅花作 STRUCTURE_STRESS_TEST；元靈若提供則只作 TEMPORAL_NUMERIC_CONTEXT，不做三套術數投票。",
            "所有 packet 皆不可重新起局／起卦／演數、改時間、換主客或更改 deterministic facts。",
            "event_metadata 是來源／賽事描述層，不可反向改寫 match_event 的起局時間。",
            "若 differentiation_audit 顯示 TEMPORAL_ONLY__UNSAFE_FOR_CROSS_FIXTURE_DIFFERENTIATION，同時不同賽事不得只靠共同時間盤輸出不同結論。",
            "若 temporal signature 相同而 event signature 不同，差異判讀必須指向 event/participant layer，不得以事後挑象冒充分辨能力。",
            "古籍原文、source review、project heuristic、football modern application 必須分層。",
            "最終判讀由 ChatGPT 完成；bundle 不包含自動勝率、固定比分或最終賽果。",
        ],
    }
    payload["bundle_sha256"] = sha256_payload(payload)
    return payload
