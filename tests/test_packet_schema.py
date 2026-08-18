import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from jsonschema import Draft202012Validator, FormatChecker

from jarvis.divination_packet import build_meihua_packet, build_qimen_packet


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "schemas" / "divination_packet_v2.schema.json").read_text(encoding="utf-8"))
VALIDATOR = Draft202012Validator(SCHEMA, format_checker=FormatChecker())


def _event() -> datetime:
    return datetime(2026, 6, 15, 12, 0, tzinfo=ZoneInfo("America/New_York"))


def _assert_valid(payload):
    errors = sorted(VALIDATOR.iter_errors(payload), key=lambda exc: list(exc.path))
    assert not errors, "\n".join(error.message for error in errors)


def test_qimen_packet_matches_v2_schema():
    packet = build_qimen_packet(
        question="測試奇門",
        event_at=_event(),
        timezone_name="America/New_York",
    )
    _assert_valid(packet)


def test_meihua_packet_matches_v2_schema():
    packet = build_meihua_packet(
        question="測試梅花",
        event_at=_event(),
        timezone_name="America/New_York",
    )
    _assert_valid(packet)
