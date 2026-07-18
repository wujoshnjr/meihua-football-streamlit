from __future__ import annotations

import re
from typing import Any

from meihua_engine import count_symbols
from version import INPUT_PROTOCOL_VERSION


BODY_SECTION_LABEL = "體方自述（起象）"
USE_SECTION_LABEL = "用方自述（起象）"
NEUTRAL_SECTION_LABEL = "賽前中性介紹（動爻）"

SELF_NARRATIVE_MIN_COUNT = 180
SELF_NARRATIVE_MAX_COUNT = 220
NEUTRAL_MIN_COUNT = 300
NEUTRAL_MAX_COUNT = 450

SELF_NARRATIVE_STRUCTURE = (
    ("整體狀態", ("目前我的整體狀態", "目前我的狀態")),
    ("士氣", ("我的士氣",)),
    ("比賽策略", ("我的比賽策略", "我的策略")),
    ("主要依靠", ("我主要依靠",)),
    ("進攻方式", ("我的進攻方式", "我的進攻主要依靠", "我的進攻")),
    ("防守方式", ("我的防守方式", "我的防守依靠", "我的防守")),
    ("最大優勢", ("我最大的優勢",)),
    ("注意事項", ("我最需要注意",)),
    ("九十分鐘目標", ("我希望在九十分鐘內", "我希望在90分鐘內")),
)


def _starts_as_team(text: str, team_name: str) -> bool:
    return bool(re.match(rf"^我是\s*{re.escape(team_name.strip())}(?:[。！!，,\s]|$)", text.strip()))


def _missing_structure(text: str) -> list[str]:
    return [
        label
        for label, accepted_phrases in SELF_NARRATIVE_STRUCTURE
        if not any(phrase in text for phrase in accepted_phrases)
    ]


def build_input_protocol_audit(
    body_name: str,
    use_name: str,
    body_text: str,
    use_text: str,
    full_text: str,
) -> dict[str, Any]:
    body_count = count_symbols(body_text)
    use_count = count_symbols(use_text)
    neutral_count = count_symbols(full_text)
    return {
        "version": INPUT_PROTOCOL_VERSION,
        "scope": "只使用賽前資訊，判斷範圍固定為九十分鐘，不含延長賽與PK。",
        "counting_note": "字數採系統固定起卦計數法；標點與空白不計。",
        "sections": {
            "body": {
                "label": BODY_SECTION_LABEL,
                "voice": "第一人稱",
                "purpose": "取體卦／下卦",
                "target_count": [SELF_NARRATIVE_MIN_COUNT, SELF_NARRATIVE_MAX_COUNT],
                "actual_count": body_count,
                "count_in_range": SELF_NARRATIVE_MIN_COUNT <= body_count <= SELF_NARRATIVE_MAX_COUNT,
                "starts_with_team_identity": _starts_as_team(body_text, body_name),
                "missing_structure": _missing_structure(body_text),
            },
            "use": {
                "label": USE_SECTION_LABEL,
                "voice": "第一人稱",
                "purpose": "取用卦／上卦",
                "target_count": [SELF_NARRATIVE_MIN_COUNT, SELF_NARRATIVE_MAX_COUNT],
                "actual_count": use_count,
                "count_in_range": SELF_NARRATIVE_MIN_COUNT <= use_count <= SELF_NARRATIVE_MAX_COUNT,
                "starts_with_team_identity": _starts_as_team(use_text, use_name),
                "missing_structure": _missing_structure(use_text),
            },
            "neutral": {
                "label": NEUTRAL_SECTION_LABEL,
                "voice": "第三人稱",
                "purpose": "取動爻",
                "target_count": [NEUTRAL_MIN_COUNT, NEUTRAL_MAX_COUNT],
                "actual_count": neutral_count,
                "count_in_range": NEUTRAL_MIN_COUNT <= neutral_count <= NEUTRAL_MAX_COUNT,
                "mentions_body_name": body_name.strip() in full_text,
                "mentions_use_name": use_name.strip() in full_text,
                "contains_first_person": "我" in full_text,
            },
        },
    }


def validate_input_protocol(
    body_name: str,
    use_name: str,
    body_text: str,
    use_text: str,
    full_text: str,
) -> list[str]:
    audit = build_input_protocol_audit(body_name, use_name, body_text, use_text, full_text)
    issues: list[str] = []
    for key, team_name in (("body", body_name), ("use", use_name)):
        section = audit["sections"][key]
        minimum, maximum = section["target_count"]
        if not section["count_in_range"]:
            issues.append(
                f"{section['label']}目前為 {section['actual_count']} 數，固定範圍為 {minimum}～{maximum} 數。"
            )
        if not section["starts_with_team_identity"]:
            issues.append(f"{section['label']}必須以「我是{team_name}。」開始。")
        if section["missing_structure"]:
            missing = "、".join(section["missing_structure"])
            issues.append(f"{section['label']}缺少固定結構：{missing}。")

    neutral = audit["sections"]["neutral"]
    minimum, maximum = neutral["target_count"]
    if not neutral["count_in_range"]:
        issues.append(
            f"{neutral['label']}目前為 {neutral['actual_count']} 數，固定範圍為 {minimum}～{maximum} 數。"
        )
    if neutral["contains_first_person"]:
        issues.append(f"{neutral['label']}必須使用第三人稱，不可出現第一人稱「我／我們」。")
    missing_names = [
        name
        for name, present in (
            (body_name, neutral["mentions_body_name"]),
            (use_name, neutral["mentions_use_name"]),
        )
        if not present
    ]
    if missing_names:
        issues.append(f"{neutral['label']}必須同時提到雙方名稱：{'、'.join(missing_names)}。")
    return issues


__all__ = [
    "BODY_SECTION_LABEL",
    "NEUTRAL_MAX_COUNT",
    "NEUTRAL_MIN_COUNT",
    "NEUTRAL_SECTION_LABEL",
    "SELF_NARRATIVE_MAX_COUNT",
    "SELF_NARRATIVE_MIN_COUNT",
    "SELF_NARRATIVE_STRUCTURE",
    "USE_SECTION_LABEL",
    "build_input_protocol_audit",
    "validate_input_protocol",
]
