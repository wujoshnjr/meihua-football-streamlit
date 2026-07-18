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
    ("客觀狀態", "目前我的客觀狀態"),
    ("士氣與比賽壓力", "我的士氣與比賽壓力"),
    ("預計比賽策略", "我的預計比賽策略"),
    ("組織支點", "我主要依靠的組織支點"),
    ("主要進攻通道", "我的主要進攻通道"),
    ("主要防守結構", "我的主要防守結構"),
    ("最大相對優勢", "我最大的相對優勢"),
    ("自身明顯限制", "我目前最明顯的限制"),
    ("對手主要威脅", "我最需要防範對手的"),
    ("九十分鐘可執行目標", "我希望在九十分鐘內"),
)

CONTROLLED_VOCABULARY = {
    "狀態評級": ("明顯正面", "略正面", "中性", "略負面", "明顯負面"),
    "主要策略": ("主動控球", "快速轉換", "直接推進", "中低位防守"),
}

PROHIBITED_RESULT_PHRASES = (
    "必勝",
    "一定能擊敗",
    "一定會擊敗",
    "希望取勝",
    "希望獲勝",
    "爭取晉級",
    "希望晉級",
    "強勢晉級",
    "創造歷史",
    "復仇",
)

POST_MATCH_MARKERS = (
    "最終比分",
    "終場比分",
    "實際比分",
    "賽後統計",
    "賽後",
    "已經晉級",
    "已遭淘汰",
)

GENERIC_ONLY_CONTENT = frozenset(
    {
        "穩定",
        "良好",
        "高昂",
        "保持高昂",
        "專注",
        "保持專注",
        "控制節奏",
        "技術",
        "團結",
        "經驗",
    }
)


def _starts_as_team(text: str, team_name: str) -> bool:
    return bool(re.match(rf"^我是\s*{re.escape(team_name.strip())}(?:[。！!，,\s]|$)", text.strip()))


def _non_empty_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def _identity_line_is_exact(line: str, team_name: str) -> bool:
    return bool(re.fullmatch(rf"我是\s*{re.escape(team_name.strip())}\s*[。！!]", line))


def _field_payload(line: str, prefix: str) -> str:
    if not line.startswith(prefix):
        return ""
    return line[len(prefix) :].strip(" ：:，,。；;！？!?…\t")


def _self_narrative_audit(team_name: str, text: str) -> dict[str, Any]:
    lines = _non_empty_lines(text)
    identity_line = lines[0] if lines else ""
    line_checks: list[dict[str, Any]] = []
    missing_structure: list[str] = []
    empty_fields: list[str] = []
    generic_fields: list[str] = []
    for position, (label, prefix) in enumerate(SELF_NARRATIVE_STRUCTURE, start=2):
        actual_line = lines[position - 1] if len(lines) >= position else ""
        in_expected_position = actual_line.startswith(prefix)
        appears_anywhere = any(line.startswith(prefix) for line in lines[1:])
        payload = _field_payload(actual_line, prefix) if in_expected_position else ""
        content_count = count_symbols(payload)
        if not appears_anywhere:
            missing_structure.append(label)
        if in_expected_position and content_count < 2:
            empty_fields.append(label)
        normalized_payload = re.sub(r"[\W_]+", "", payload)
        if normalized_payload in GENERIC_ONLY_CONTENT:
            generic_fields.append(label)
        line_checks.append(
            {
                "line": position,
                "field": label,
                "required_prefix": prefix,
                "in_expected_position": in_expected_position,
                "content_count": content_count,
            }
        )

    prohibited_phrases = [phrase for phrase in PROHIBITED_RESULT_PHRASES if phrase in text]
    controlled_matches = {
        category: [term for term in terms if term in text]
        for category, terms in CONTROLLED_VOCABULARY.items()
    }
    return {
        "expected_non_empty_lines": 11,
        "actual_non_empty_lines": len(lines),
        "line_count_valid": len(lines) == 11,
        "starts_with_team_identity": _starts_as_team(text, team_name),
        "identity_line_isolated": _identity_line_is_exact(identity_line, team_name),
        "line_order_valid": len(lines) == 11
        and all(check["in_expected_position"] for check in line_checks),
        "missing_structure": missing_structure,
        "empty_fields": empty_fields,
        "line_checks": line_checks,
        "prohibited_result_phrases": prohibited_phrases,
        "post_match_markers": [marker for marker in POST_MATCH_MARKERS if marker in text],
        "controlled_vocabulary_matches": controlled_matches,
        "quality_warnings": [
            f"{field}只使用泛用詞，建議改成可核對且能區分本場的訊號。"
            for field in generic_fields
        ],
    }


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
    body_audit = _self_narrative_audit(body_name, body_text)
    use_audit = _self_narrative_audit(use_name, use_text)
    return {
        "version": INPUT_PROTOCOL_VERSION,
        "scope": "只使用賽前資訊，判斷範圍固定為九十分鐘，不含延長賽與PK。",
        "counting_note": "字數採系統固定起卦計數法；標點與空白不計。",
        "purpose_boundary": "固定格式只降低文字噪音並提高一致性、可重複性與可回測性，不宣稱某種寫法能提高預測準確率。",
        "freeze_policy": "建議開賽前六小時凍結；其後只有重大傷停或先發變化才重做，且體用雙方必須一起更新。",
        "versioning_policy": "保存三段原文與輸入規格版本；起卦後不得因卦象不合直覺而替換同義詞、補句或重新計數。",
        "controlled_vocabulary": CONTROLLED_VOCABULARY,
        "hard_rules": [
            "體用雙方使用完全相同的十一行結構。",
            "每個非空行只承載一個固定欄位，順序不得調換。",
            "自己的限制與需要防範的對手威脅必須分開。",
            "不使用必勝、取勝晉級、復仇等情緒化或結果導向文字。",
            "只用賽前資訊，排卦後保留原始版本。",
        ],
        "post_match_markers": [
            marker
            for marker in POST_MATCH_MARKERS
            if marker in body_text or marker in use_text or marker in full_text
        ],
        "sections": {
            "body": {
                "label": BODY_SECTION_LABEL,
                "voice": "第一人稱",
                "purpose": "取體卦／下卦",
                "target_count": [SELF_NARRATIVE_MIN_COUNT, SELF_NARRATIVE_MAX_COUNT],
                "actual_count": body_count,
                "count_in_range": SELF_NARRATIVE_MIN_COUNT <= body_count <= SELF_NARRATIVE_MAX_COUNT,
                **body_audit,
            },
            "use": {
                "label": USE_SECTION_LABEL,
                "voice": "第一人稱",
                "purpose": "取用卦／上卦",
                "target_count": [SELF_NARRATIVE_MIN_COUNT, SELF_NARRATIVE_MAX_COUNT],
                "actual_count": use_count,
                "count_in_range": SELF_NARRATIVE_MIN_COUNT <= use_count <= SELF_NARRATIVE_MAX_COUNT,
                **use_audit,
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
                "post_match_markers": [marker for marker in POST_MATCH_MARKERS if marker in full_text],
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
        elif not section["identity_line_isolated"]:
            issues.append(f"{section['label']}第一行必須只寫「我是{team_name}。」。")
        if not section["line_count_valid"]:
            issues.append(
                f"{section['label']}必須有 11 個非空獨立行，目前為 {section['actual_non_empty_lines']} 行。"
            )
        if section["missing_structure"]:
            missing = "、".join(section["missing_structure"])
            issues.append(f"{section['label']}缺少固定結構：{missing}。")
        if not section["line_order_valid"] and not section["missing_structure"]:
            issues.append(f"{section['label']}十一個欄位的行序或固定開頭不正確。")
        if section["empty_fields"]:
            empty = "、".join(section["empty_fields"])
            issues.append(f"{section['label']}下列欄位尚未填入實質內容：{empty}。")
        if section["prohibited_result_phrases"]:
            phrases = "、".join(section["prohibited_result_phrases"])
            issues.append(f"{section['label']}含結果導向或情緒化詞語：{phrases}。")

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
    post_match_markers = sorted(
        {
            marker
            for section in audit["sections"].values()
            for marker in section.get("post_match_markers", [])
        }
    )
    if post_match_markers:
        issues.append(f"三段內容含疑似賽後資訊：{'、'.join(post_match_markers)}。")
    return issues


__all__ = [
    "BODY_SECTION_LABEL",
    "CONTROLLED_VOCABULARY",
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
