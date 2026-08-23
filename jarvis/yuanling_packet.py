from __future__ import annotations

from datetime import datetime
from typing import Any

from jarvis.provenance import sha256_payload
from yuanling.riqimen import build_riqimen_base
from yuanling.yanshu_qiyao import build_qiyao_review


YUANLING_PACKET_VERSION = "YUANLING_YANSHU_PACKET_V1"


def _packet_hash(payload: dict[str, Any]) -> str:
    copy = dict(payload)
    copy.pop("packet_sha256", None)
    return sha256_payload(copy)


def build_yuanling_yanshu_packet(
    *,
    question: str,
    event_at: datetime,
    timezone_name: str,
    mode: str = "QIYAO_RAW",
    number_palace: int | None = None,
    number_chief_star_number: int | None = None,
    number_chief_landing_palace: int | None = None,
    flying_star: Any = None,
    entry_door: Any = None,
    daily_star_number: int | None = None,
) -> dict[str, Any]:
    if not question.strip():
        raise ValueError("問題不可空白")
    if event_at.tzinfo is None:
        raise ValueError("event_at 必須含時區")

    qiyao = build_qiyao_review(
        event_at,
        timezone_name,
        mode=mode,
        number_palace=number_palace,
        number_chief_star_number=number_chief_star_number,
        number_chief_landing_palace=number_chief_landing_palace,
        flying_star=flying_star,
        entry_door=entry_door,
        daily_star_number=daily_star_number,
    )
    riqimen = build_riqimen_base(event_at, timezone_name) if mode == "RIQIMEN_QIYAO_EXPERIMENT" else None

    payload: dict[str, Any] = {
        "schema_version": YUANLING_PACKET_VERSION,
        "packet_purpose": "SOURCE_AWARE_NUMERIC_DIVINATION_FACTS__CHATGPT_INTERPRETS",
        "system": "YUANLING_YANSHU_QIYAO",
        "question": {"text": question.strip(), "category": "numeric_divination"},
        "event": {
            "datetime": qiyao["event"]["local_datetime"],
            "timezone": qiyao["event"]["timezone"],
        },
        "mode": mode,
        "qiyao_review": qiyao,
        "riqimen_base": riqimen,
        "ai_interpretation_contract": {
            "read_order": [
                "source/method boundary",
                "seven qiyao factors",
                "number-chief landing state",
                "riqimen base only when experiment mode is active",
                "uncertainty and unresolved algorithms",
                "final human/ChatGPT interpretation"
            ],
            "rules": [
                "Do not merge QIYAO_RAW and RI-QIMEN into one classical method claim.",
                "Do not infer missing Yuanling algorithms from the existing Shijia engine.",
                "Do not convert a palace number directly into goals or a scoreline.",
                "Do not use post-match results to select or mutate numeric candidates.",
                "Unresolved fields remain unresolved; uncertainty is evidence, not a defect to hide."
            ],
            "score_synthesis": "DEFERRED_UNTIL_BLIND_TEST_PROTOCOL",
        },
        "forbidden_outputs": [
            "AUTOMATIC_FOOTBALL_SCORE_FROM_PALACE_NUMBER",
            "AUTOMATIC_WIN_PROBABILITY",
            "POSTMATCH_RULE_FITTING",
            "SILENT_SHIJIA_STAR_SUBSTITUTION"
        ],
    }
    payload["packet_sha256"] = _packet_hash(payload)
    return payload


def verify_yuanling_packet_integrity(packet: dict[str, Any]) -> bool:
    return bool(packet.get("packet_sha256")) and packet["packet_sha256"] == _packet_hash(packet)
