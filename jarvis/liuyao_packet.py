from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable

from jarvis.provenance import sha256_payload
from liuyao.engine import LIUYAO_CAST_METHOD, LIUYAO_ENGINE_VERSION, cast_liuyao
from liuyao.review import LIUYAO_REVIEW_VERSION, build_liuyao_review


LIUYAO_PACKET_VERSION = "LIUYAO_PACKET_V1"


def _packet_hash(payload: dict[str, Any]) -> str:
    copy = dict(payload)
    copy.pop("packet_sha256", None)
    return sha256_payload(copy)


def build_liuyao_packet(
    *,
    question: str,
    line_values: Iterable[int],
    event_at: datetime,
    timezone_name: str,
    question_category: str = "GENERAL",
) -> dict[str, Any]:
    if not question.strip():
        raise ValueError("問題不可空白")
    if event_at.tzinfo is None:
        raise ValueError("event_at 必須含時區")

    chart = cast_liuyao(line_values, event_at, timezone_name)
    review = build_liuyao_review(chart, question_category=question_category)

    payload: dict[str, Any] = {
        "schema_version": LIUYAO_PACKET_VERSION,
        "packet_purpose": "SOURCE_AWARE_LIUYAO_CAST__CHATGPT_INTERPRETS",
        "system": "LIUYAO_WENWANGGUA",
        "question": {
            "text": question.strip(),
            "category": question_category.strip().upper() or "GENERAL",
        },
        "event": {
            "datetime": chart.event_local_at.isoformat(),
            "timezone": chart.timezone_name,
            "normalization": "ACTUAL_CAST_EVENT_LOCAL_TIME",
        },
        "method": {
            "engine_version": LIUYAO_ENGINE_VERSION,
            "cast_method": LIUYAO_CAST_METHOD,
            "line_input_order": "BOTTOM_TO_TOP__FIRST_CAST_IS_LINE_1",
            "line_values": {
                "6": "老陰，動，變陽",
                "7": "少陽，靜",
                "8": "少陰，靜",
                "9": "老陽，動，變陰",
            },
            "authority": "SOURCE_GROUNDED_CORE__REVIEW_LAYERS_SEPARATED",
        },
        "chart": chart.to_dict(),
        "review": {
            "schema_version": review.schema_version,
            "status": review.status,
            "question_role": review.question_role,
            "use_god_review": review.use_god_review,
            "strength_review": review.strength_review,
            "motion_review": review.motion_review,
            "source_audit": review.source_audit,
            "contradiction_register": review.contradiction_register,
            "uncertainty_register": review.uncertainty_register,
        },
        "knowledge_context": [
            {
                "kind": "liuyao_method_boundary",
                "review_version": LIUYAO_REVIEW_VERSION,
                "core": [
                    "三錢／手動 6-7-8-9 六次，初爻到上爻",
                    "本卦／變卦",
                    "納甲",
                    "八宮歸屬與世應",
                    "六親",
                    "六神",
                    "旬空",
                    "月建／日辰直接關係",
                    "動爻變爻",
                    "伏神候選",
                ],
                "advanced_review_not_collapsed_into_core": [
                    "完整旺衰定級",
                    "暗動／日破最終判別",
                    "用神強弱與原神忌神仇神",
                    "三合成局／進退神／墓絕",
                    "伏吟反吟",
                    "神煞",
                    "應期",
                    "專項占法",
                ],
            },
            {
                "kind": "liuyao_primary_sources",
                "sources": review.source_audit["primary_classical"],
            },
        ],
        "ai_interpretation_contract": [
            "不得重新起卦、改六次投擲結果、改事件時間或重算成另一套納甲。",
            "先驗排卦：本變卦、八宮、世應、納甲、六親、六神、旬空、月建日辰與動變。",
            "再依問題類別選用神；若 question_role 未映射或屬足球 adaptation，不可假裝古法已唯一指定。",
            "月建與日辰同時審，不用單一符號投票；月破、旬空、日沖、明動可同時存在。",
            "日沖靜爻不可一律叫暗動，必須結合旺衰；V1 若未解足夠就保留不確定。",
            "六神只作附合象意，不得凌駕五行生克、用神旺衰與動變。",
            "變爻六親依正卦卦宮五行；不得改用變卦自身卦宮重算。",
            "伏神候選不等於有用；須再審飛神、日月、空破與生克。",
            "足球時，世應／子孫官鬼的主客映射只是 candidate protocol，必須同 cohort 比較，不能逐場挑選。",
            "古籍原則、後世師承、影片技巧與 JARVIS project adaptation 必須分層陳述。",
            "不得因知道結果而改用神、改暗動判準、改主客映射或挑另一套起卦法。",
        ],
        "forbidden_outputs": [
            "AUTO_RESULT_FROM_SINGLE_SIX_SPIRIT",
            "AUTO_RESULT_FROM_SINGLE_VOID_OR_CLASH",
            "EVERY_DAY_CLASH_STATIC_LINE_IS_DARK_MOVING",
            "FOOTBALL_MAPPING_PRESENTED_AS_CLASSICAL_CERTAINTY",
            "POST_RESULT_USE_GOD_SWITCHING",
            "POST_RESULT_CAST_METHOD_SWITCHING",
            "UNVERIFIED_USER_VIDEO_RULE_PROMOTED_TO_CORE",
        ],
    }
    payload["packet_sha256"] = _packet_hash(payload)
    return payload


def verify_liuyao_packet_integrity(packet: dict[str, Any]) -> bool:
    return bool(packet.get("packet_sha256")) and packet["packet_sha256"] == _packet_hash(packet)
