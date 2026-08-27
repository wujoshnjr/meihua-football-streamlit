from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from jarvis.case_bundle import (
    DIVINATION_CASE_BUNDLE_VERSION,
    MATCH_EVENT_VERSION,
    build_divination_case_bundle,
    verify_bundle_integrity,
    verify_packet_integrity,
)
from jarvis.divination_packet import build_meihua_packet, build_qimen_packet
from jarvis.yuanling_packet import build_yuanling_yanshu_packet


def _event() -> datetime:
    return datetime(2026, 6, 15, 12, 0, tzinfo=ZoneInfo("America/New_York"))


def _qimen(event: datetime | None = None, away_team: str = "維德角"):
    return build_qimen_packet(
        question="正規時間勝負與候選比分如何？",
        event_at=event or _event(),
        timezone_name="America/New_York",
        category="football_match",
        home_team="西班牙",
        away_team=away_team,
    )


def _meihua(event: datetime | None = None, away_team: str = "維德角"):
    return build_meihua_packet(
        question="這場比賽的結構、轉折與反證如何？",
        event_at=event or _event(),
        timezone_name="America/New_York",
        category="football_match",
        home_team="西班牙",
        away_team=away_team,
    )


def test_case_bundle_aligns_same_event_while_allowing_different_questions():
    qimen = _qimen()
    meihua = _meihua()

    first = build_divination_case_bundle(
        qimen,
        meihua,
        event_metadata={
            "competition": "測試賽事",
            "stage": "小組賽",
            "kickoff_basis": "OFFICIAL_SCHEDULED_KICKOFF",
            "time_verification_status": "VERIFIED",
            "mode": "PREMATCH",
        },
    )
    second = build_divination_case_bundle(
        qimen,
        meihua,
        event_metadata={
            "competition": "測試賽事",
            "stage": "小組賽",
            "kickoff_basis": "OFFICIAL_SCHEDULED_KICKOFF",
            "time_verification_status": "VERIFIED",
            "mode": "PREMATCH",
        },
    )

    assert first["schema_version"] == DIVINATION_CASE_BUNDLE_VERSION
    assert first["match_event"]["schema_version"] == MATCH_EVENT_VERSION
    assert first["alignment_audit"]["status"] == "PASS"
    assert all(row["match"] for row in first["alignment_audit"]["fields"].values())
    assert first["alignment_audit"]["packet_integrity"]["qimen"]["status"] == "PASS"
    assert first["alignment_audit"]["packet_integrity"]["meihua"]["status"] == "PASS"
    assert first["interpretation_roles"]["qimen"]["role"] == "RESULT_ENGINE_INPUT"
    assert first["interpretation_roles"]["meihua"]["role"] == "STRUCTURE_STRESS_TEST"
    assert first["interpretation_roles"]["yuanling"]["role"] == "TEMPORAL_NUMERIC_CONTEXT"
    assert first["interpretation_roles"]["yuanling"]["status"] == "NOT_INCLUDED"
    assert first["interpretation_roles"]["final"]["role"] == "CHATGPT_FINAL_SYNTHESIS"
    assert first["qimen_packet_sha256"] == qimen["packet_sha256"]
    assert first["meihua_packet_sha256"] == meihua["packet_sha256"]
    assert first["bundle_sha256"] == second["bundle_sha256"]
    assert first["event_metadata"]["competition"] == "測試賽事"
    assert verify_bundle_integrity(first)["status"] == "PASS"
    assert qimen["question"]["text"] != meihua["question"]["text"]


def test_case_bundle_rejects_time_mismatch():
    qimen = _qimen()
    meihua = _meihua(_event() + timedelta(minutes=1))

    with pytest.raises(ValueError, match="CASE_ALIGNMENT_FAIL"):
        build_divination_case_bundle(qimen, meihua)


def test_case_bundle_rejects_team_mismatch():
    qimen = _qimen()
    meihua = _meihua(away_team="葡萄牙")

    with pytest.raises(ValueError, match="CASE_ALIGNMENT_FAIL"):
        build_divination_case_bundle(qimen, meihua)


def test_case_bundle_rejects_tampered_packet_sha():
    qimen = _qimen()
    meihua = _meihua()
    tampered = dict(qimen)
    tampered["question"] = {"text": "被竄改", "category": "football_match"}

    assert verify_packet_integrity(tampered)["status"] == "FAIL"
    with pytest.raises(ValueError, match="QIMEN_PACKET_SHA_INVALID"):
        build_divination_case_bundle(tampered, meihua)


def test_case_bundle_can_include_yuanling_as_temporal_sibling():
    qimen = _qimen()
    meihua = _meihua()
    yuanling = build_yuanling_yanshu_packet(
        question="整理共同時段的元靈七要數勢，不直接輸出比分。",
        event_at=_event(),
        timezone_name="America/New_York",
        mode="QIYAO_RAW",
    )

    bundle = build_divination_case_bundle(
        qimen,
        meihua,
        yuanling_packet=yuanling,
    )

    assert bundle["schema_version"] == "DIVINATION_CASE_BUNDLE_V2"
    assert bundle["yuanling_packet_sha256"] == yuanling["packet_sha256"]
    assert bundle["alignment_audit"]["packet_integrity"]["yuanling"]["status"] == "PASS"
    assert bundle["alignment_audit"]["yuanling_temporal_alignment"]["datetime"]["match"] is True
    assert bundle["alignment_audit"]["yuanling_temporal_alignment"]["timezone"]["match"] is True
    assert bundle["interpretation_roles"]["yuanling"]["status"] == "INCLUDED"


def test_case_bundle_rejects_yuanling_time_mismatch():
    qimen = _qimen()
    meihua = _meihua()
    yuanling = build_yuanling_yanshu_packet(
        question="整理共同時段數勢。",
        event_at=_event() + timedelta(minutes=1),
        timezone_name="America/New_York",
        mode="QIYAO_RAW",
    )

    with pytest.raises(ValueError, match="YUANLING"):
        build_divination_case_bundle(qimen, meihua, yuanling_packet=yuanling)
