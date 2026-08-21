import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from jsonschema import Draft202012Validator, FormatChecker

from jarvis.case_bundle import build_divination_case_bundle
from jarvis.divination_packet import build_meihua_packet, build_qimen_packet


ROOT = Path(__file__).resolve().parents[1]
PACKET_SCHEMA = json.loads((ROOT / "schemas" / "divination_packet_v2.schema.json").read_text(encoding="utf-8"))
CASE_SCHEMA = json.loads((ROOT / "schemas" / "divination_case_bundle_v1.schema.json").read_text(encoding="utf-8"))
PACKET_VALIDATOR = Draft202012Validator(PACKET_SCHEMA, format_checker=FormatChecker())
CASE_VALIDATOR = Draft202012Validator(CASE_SCHEMA, format_checker=FormatChecker())


def _event() -> datetime:
    return datetime(2026, 6, 15, 12, 0, tzinfo=ZoneInfo("America/New_York"))


def _assert_valid(validator, payload):
    errors = sorted(validator.iter_errors(payload), key=lambda exc: list(exc.path))
    assert not errors, "\n".join(error.message for error in errors)


def test_qimen_packet_matches_v2_schema():
    packet = build_qimen_packet(
        question="測試奇門",
        event_at=_event(),
        timezone_name="America/New_York",
    )
    _assert_valid(PACKET_VALIDATOR, packet)


def test_meihua_packet_matches_v2_schema():
    packet = build_meihua_packet(
        question="測試梅花",
        event_at=_event(),
        timezone_name="America/New_York",
    )
    _assert_valid(PACKET_VALIDATOR, packet)


def test_same_event_case_bundle_matches_v1_schema():
    qimen = build_qimen_packet(
        question="正規時間勝負如何？",
        event_at=_event(),
        timezone_name="America/New_York",
        category="football_match",
        home_team="西班牙",
        away_team="維德角",
    )
    meihua = build_meihua_packet(
        question="結構、轉折與反證如何？",
        event_at=_event(),
        timezone_name="America/New_York",
        category="football_match",
        home_team="西班牙",
        away_team="維德角",
    )
    bundle = build_divination_case_bundle(qimen, meihua)
    _assert_valid(CASE_VALIDATOR, bundle)
