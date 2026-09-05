"""Shared import/export gates. Validation never edits or recasts an artifact."""
from __future__ import annotations

import json
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from jarvis.provenance import sha256_payload
from jarvis.time import aware_event_local_datetime

ROOT = Path(__file__).resolve().parents[1]
MAX_UPLOAD_BYTES = 8 * 1024 * 1024
SCHEMAS = {
    "DIVINATION_PACKET_V2": "divination_packet_v2.schema.json",
    "LIUYAO_PACKET_V1": "liuyao_packet_v1.schema.json",
    "YUANLING_YANSHU_PACKET_V1_3": "yuanling_yanshu_packet_v1_3.schema.json",
    "DIVINATION_CASE_BUNDLE_V2": "divination_case_bundle_v2.schema.json",
    "DIVINATION_CASE_BUNDLE_V3": "divination_case_bundle_v3.schema.json",
}


def load_json_object(raw: bytes | str, *, max_bytes: int = MAX_UPLOAD_BYTES) -> dict[str, Any]:
    if len(raw.encode("utf-8") if isinstance(raw, str) else raw) > max_bytes:
        raise ValueError(f"JSON 檔案超過 {max_bytes // (1024 * 1024)} MiB 上限")

    def invalid_constant(value: str):
        raise ValueError(f"JSON 不接受非有限數值：{value}")

    def unique_keys(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"JSON 欄位重複：{key}")
            result[key] = value
        return result

    try:
        result = json.loads(raw, parse_constant=invalid_constant, object_pairs_hook=unique_keys)
    except (UnicodeError, RecursionError, json.JSONDecodeError) as exc:
        raise ValueError("無法讀取 JSON，請檢查編碼與結構") from exc
    if not isinstance(result, dict):
        raise ValueError("JSON 最外層必須是 object")
    return result


@lru_cache(maxsize=16)
def _validator(version: str):
    from jsonschema import Draft202012Validator, FormatChecker

    filename = SCHEMAS.get(version)
    if filename is None:
        raise ValueError(f"不支援的 artifact schema：{version}")
    schema = json.loads((ROOT / "schemas" / filename).read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def validate_schema(payload: Any) -> None:
    if not isinstance(payload, dict):
        raise ValueError("artifact 最外層必須是 object")
    errors = list(_validator(str(payload.get("schema_version", ""))).iter_errors(payload))
    if errors:
        details = [f"{'/'.join(map(str, e.absolute_path)) or '$'}: {e.message}" for e in errors[:6]]
        raise ValueError("SCHEMA_INVALID: " + "；".join(details))


def _check_sha(payload: dict, key: str) -> None:
    expected = payload.get(key)
    actual = sha256_payload({k: v for k, v in payload.items() if k != key})
    if not expected or expected != actual:
        raise ValueError(f"{key.upper()}_MISMATCH")


def _same(value: Any, expected: Any, field: str) -> None:
    if value != expected:
        raise ValueError(f"SEMANTIC_MISMATCH: {field}")


def _check_local_event(event: dict) -> None:
    value = datetime.fromisoformat(event["datetime"])
    if value.tzinfo is None:
        raise ValueError("event.datetime 必須含 UTC offset")
    local = aware_event_local_datetime(value, event["timezone"])
    _same((value.replace(tzinfo=None), value.utcoffset()),
          (local.replace(tzinfo=None), local.utcoffset()), "event timezone / offset")


def _check_clock(payload: dict, date_key: str, zone_key: str, event: dict, label: str) -> None:
    _same(payload[date_key], event["datetime"], f"{label}.{date_key}")
    _same(payload[zone_key], event["timezone"], f"{label}.{zone_key}")


def _packet_semantics(packet: dict) -> None:
    from jarvis.case_bundle import build_match_event_identity
    from jarvis.event_layers import build_football_event_identity, build_qimen_coach_participant_layer

    event = packet["event"]
    _check_local_event(event)
    system = packet["system"]
    if system == "QIMEN_DUNJIA":
        chart = packet["chart"]
        _check_clock(chart["calendar"], "local_datetime", "timezone_name", event, "chart.calendar")
        _same(set(chart["palaces"]), {str(i) for i in range(1, 10)}, "nine palaces")
    elif system == "MEIHUA_YISHU":
        _check_clock(packet["hexagram"], "event_local_at", "timezone_name", event, "hexagram")
        _check_clock(packet["meihua_method_audit"]["time_convention"],
                     "event_local_datetime", "timezone", event, "time_convention")
        timeline = packet.get("temporal_precision_audit")
        if timeline:
            _same(timeline["anchor_cast"]["local_datetime"], event["datetime"], "timeline.anchor")
    elif system == "LIUYAO_WENWANGGUA":
        _check_clock(packet["chart"], "event_local_at", "timezone_name", event, "chart")
    elif system == "YUANLING_YANSHU_QIYAO":
        _check_clock(packet["qiyao_review"]["event"], "local_datetime", "timezone", event, "qiyao")

    if packet["question"]["category"] != "football_match":
        return
    fixture = packet["football_fixture"]
    canonical = build_match_event_identity(
        home_team=fixture["home_team"], away_team=fixture["away_team"],
        event_datetime=datetime.fromisoformat(event["datetime"]), timezone_name=event["timezone"],
    )
    _same(packet["match_event"], canonical, "match_event")
    identity = packet.get("event_identity_layer") or {}
    if identity.get("status") == "CANONICAL_PREMATCH_IDENTITY_READY":
        _same(identity, build_football_event_identity(identity["canonical_fields"]), "event_identity_layer")
    if system == "QIMEN_DUNJIA":
        host = packet["host_guest"]
        for side in ("home", "away"):
            _same(host[f"{side}_team"], fixture[f"{side}_team"], f"host_guest.{side}_team")
        participant = packet.get("participant_layer") or {}
        if participant.get("status") == "READY":
            chart = packet["chart"]
            board = SimpleNamespace(
                chief_star_palace=chart["chief_star_palace"],
                palaces={int(k): SimpleNamespace(**v) for k, v in chart["palaces"].items()},
                patterns=[SimpleNamespace(**v) for v in chart["patterns"]],
            )
            expected = build_qimen_coach_participant_layer(board, participant["identity"])
            _same(participant, expected, "participant_layer")


def validate_packet(packet: Any, *, expected_system: str | None = None) -> dict:
    validate_schema(packet)
    if "BUNDLE" in packet["schema_version"]:
        raise ValueError("這個入口需要單術數 packet")
    _check_sha(packet, "packet_sha256")
    if expected_system and packet["system"] != expected_system:
        raise ValueError(f"packet.system 必須是 {expected_system}")
    try:
        _packet_semantics(packet)
    except (KeyError, TypeError, AttributeError, IndexError) as exc:
        raise ValueError(f"PACKET_STRUCTURE_INVALID: {exc}") from exc
    return packet


def validate_bundle(bundle: Any) -> dict:
    from jarvis.event_layers import build_differentiation_audit

    validate_schema(bundle)
    if bundle["schema_version"] not in {"DIVINATION_CASE_BUNDLE_V2", "DIVINATION_CASE_BUNDLE_V3"}:
        raise ValueError("這個入口需要 Case Bundle V2 / V3")
    _check_sha(bundle, "bundle_sha256")
    q = validate_packet(bundle["qimen_packet"], expected_system="QIMEN_DUNJIA")
    m = validate_packet(bundle["meihua_packet"], expected_system="MEIHUA_YISHU")
    if any(p["question"]["category"] != "football_match" for p in (q, m)):
        raise ValueError("Case Bundle 只接受 football_match packet")
    _same(q["match_event"], m["match_event"], "qimen / meihua event")
    _same(bundle["match_event"], q["match_event"], "bundle.match_event")
    y = bundle.get("yuanling_packet")
    if y is not None:
        validate_packet(y, expected_system="YUANLING_YANSHU_QIYAO")
        for key in ("datetime", "timezone"):
            _same(y["event"][key], q["event"][key], f"yuanling.{key}")
    for name, packet in (("qimen", q), ("meihua", m), ("yuanling", y)):
        _same(bundle.get(f"{name}_packet_sha256"), packet["packet_sha256"] if packet else None,
              f"bundle.{name}_packet_sha256")
        integrity = bundle["alignment_audit"]["packet_integrity"].get(name)
        if packet:
            _same(integrity, {"status": "PASS", "reason": "MATCH", "expected": packet["packet_sha256"],
                              "actual": packet["packet_sha256"]}, f"alignment.{name}.integrity")
        else:
            _same(integrity, None, f"alignment.{name}.integrity")
    expected = build_differentiation_audit(q, m, y, legacy=bundle["schema_version"].endswith("_V2"))
    _same(bundle["differentiation_audit"], expected, "differentiation_audit")
    for field in ("home_team", "away_team", "event_datetime", "timezone", "match_event_sha256"):
        value = q["match_event"][field]
        _same(bundle["alignment_audit"]["fields"].get(field),
              {"qimen": value, "meihua": value, "match": True}, f"alignment.{field}")
    return bundle
