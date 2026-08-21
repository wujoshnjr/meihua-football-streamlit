from __future__ import annotations

from datetime import datetime
from typing import Any

from jarvis.provenance import sha256_payload

MATCH_EVENT_VERSION = "MATCH_EVENT_V1"
DIVINATION_CASE_BUNDLE_VERSION = "DIVINATION_CASE_BUNDLE_V1"


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


def build_divination_case_bundle(
    qimen_packet: dict[str, Any],
    meihua_packet: dict[str, Any],
) -> dict[str, Any]:
    """Join Qimen and Meihua packets only when they describe the same match."""

    if qimen_packet.get("system") != "QIMEN_DUNJIA":
        raise ValueError("CASE_ALIGNMENT_FAIL: qimen_packet.system 必須是 QIMEN_DUNJIA")
    if meihua_packet.get("system") != "MEIHUA_YISHU":
        raise ValueError("CASE_ALIGNMENT_FAIL: meihua_packet.system 必須是 MEIHUA_YISHU")

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

    payload: dict[str, Any] = {
        "schema_version": DIVINATION_CASE_BUNDLE_VERSION,
        "packet_purpose": "SAME_EVENT_QIMEN_MEIHUA_HANDOFF__CHATGPT_INTERPRETS",
        "match_event": qimen_event,
        "alignment_audit": {
            "status": "PASS",
            "checked_fields": list(fields),
            "fields": alignment,
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
            "final": {
                "role": "CHATGPT_FINAL_SYNTHESIS",
                "rule": "ChatGPT 保留矛盾與不確定性後做最終合參；不可重新起局或起卦。",
            },
        },
        "qimen_packet_sha256": qimen_packet.get("packet_sha256"),
        "meihua_packet_sha256": meihua_packet.get("packet_sha256"),
        "qimen_packet": qimen_packet,
        "meihua_packet": meihua_packet,
        "ai_handoff_contract": [
            "先做 alignment_audit；若不是 PASS，停止合參。",
            "奇門作 RESULT_ENGINE_INPUT；梅花作 STRUCTURE_STRESS_TEST，不做兩套術數投票。",
            "兩份 packet 皆不可重新起局／起卦、改時間、換主客或更改 deterministic chart facts。",
            "古籍原文、source review、project heuristic、football modern application 必須分層。",
            "最終判讀由 ChatGPT 完成；bundle 不包含自動勝率、固定比分或最終賽果。",
        ],
    }
    payload["bundle_sha256"] = sha256_payload(payload)
    return payload
