from __future__ import annotations

from datetime import datetime
from typing import Any

from jarvis.provenance import sha256_payload
from jarvis.yuanling_vault import yuanling_packet_knowledge_context
from yuanling.riqimen import build_riqimen_base
from yuanling.yanshu_qiyao import build_qiyao_review


YUANLING_PACKET_VERSION = "YUANLING_YANSHU_PACKET_V1_3"


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
    riqimen = (
        build_riqimen_base(event_at, timezone_name)
        if mode == "RIQIMEN_QIYAO_EXPERIMENT"
        else None
    )
    knowledge_context = yuanling_packet_knowledge_context(mode)

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
        "knowledge_context": knowledge_context,
        "ai_interpretation_contract": {
            "read_order": [
                "knowledge_context method separation and source authority",
                "seven qiyao primary factors",
                "source-crosschecked number-chief/flying-star/value-day-star role resolution",
                "number-chief landing state",
                "volume-2 door/stem source context",
                "volume-3 numeric-star shortcut/response/value-day context",
                "collateral candidate reconstruction and textual-variant warning",
                "riqimen sibling plus chuangong algorithm-resolution only when experiment mode is active",
                "work-index coverage versus materialized-source distinction",
                "remaining uncertainty and authority gaps",
                "final human/ChatGPT interpretation",
            ],
            "rules": [
                "Do not merge QIYAO_RAW and RI-QIMEN into one classical method claim.",
                "For football, treat deterministic Qiyao time-derived facts as a shared temporal environment; never use identical temporal input alone to manufacture different fixture outcomes.",
                "Qiyao review and Ri-Qimen are sibling objects; neither is silently nested into the other.",
                "Do not infer missing Yuanling algorithms from the existing Shijia engine.",
                "Treat star_role_resolution as source-crosschecked relationship evidence, not as permission to overwrite raw primary slots.",
                "Preserve the Yuanling 乾宮黑星 versus Qimen-Baojian 坤宮黑星 textual variant explicitly.",
                "Ri-Qimen chuangong uses its own numeric nine-palace forward traversal including center; never substitute the production eight-palace rotating ring.",
                "Keep Ri-Qimen 天蓬/天芮... and Yanshu 一白/二黑... in separate star registries.",
                "Classical source sections are evidence context, not automatic football outputs.",
                "Do not collapse conflicting chapter-specific numeric-star meanings into one fixed good/bad label.",
                "Do not convert a palace number, daily-star number, or Shefu number association directly into goals or a scoreline.",
                "Do not use post-match results to select chapters, rules, or numeric candidates.",
                "Collateral candidates may not be promoted into primary Yuanling facts without an explicit method-version change.",
                "Indexed table-of-contents coverage is not equivalent to full rule materialization.",
                "Unresolved fields remain visible; uncertainty is evidence, not a defect to hide.",
            ],
            "score_synthesis": "DEFERRED_UNTIL_BLIND_TEST_PROTOCOL",
        },
        "forbidden_outputs": [
            "AUTOMATIC_FOOTBALL_SCORE_FROM_PALACE_NUMBER",
            "AUTOMATIC_WIN_PROBABILITY",
            "POSTMATCH_RULE_FITTING",
            "SILENT_SHIJIA_STAR_SUBSTITUTION",
            "COLLATERAL_CANDIDATE_PROMOTED_TO_PRIMARY_FACT",
            "SHEFU_NUMBER_ASSOCIATION_TO_FOOTBALL_GOALS",
            "TABLE_OF_CONTENTS_INDEX_PROMOTED_TO_RULE",
            "CHAPTER_PICKING_BY_POSTMATCH_RESULT",
            "TEXTUAL_VARIANT_SILENTLY_NORMALIZED",
            "RIQIMEN_PRODUCTION_RING_SUBSTITUTED_FOR_CHUANGONG",
        ],
    }
    payload["packet_sha256"] = _packet_hash(payload)
    return payload


def verify_yuanling_packet_integrity(packet: dict[str, Any]) -> bool:
    return bool(packet.get("packet_sha256")) and packet["packet_sha256"] == _packet_hash(packet)
