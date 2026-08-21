from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from .zhouyi import zhouyi_hexagram, zhouyi_line_semantic_profile


ROOT = Path(__file__).resolve().parents[1]
LINE_ROLE_PATH = ROOT / "knowledge" / "meihua_line_roles.json"

FAVORABLE_MARKERS = {"auspicious", "favorable_action", "success_flow", "no_blame"}
RISK_MARKERS = {"danger", "regret", "difficulty"}


@lru_cache(maxsize=1)
def _line_roles() -> dict[int, dict[str, Any]]:
    rows = json.loads(LINE_ROLE_PATH.read_text(encoding="utf-8"))["line_roles"]
    return {int(row["line"]): row for row in rows}


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def _conditional_tendency(marker_ids: set[str]) -> tuple[str, str]:
    favorable = marker_ids & FAVORABLE_MARKERS
    risk = marker_ids & RISK_MARKERS
    if favorable and risk:
        return (
            "MIXED_CONDITIONAL",
            "原文同時具有允許／有利與風險／悔吝訊號；成立條件與限制必須一起讀，不得擷取單一吉凶字。",
        )
    if favorable:
        return (
            "CONDITIONALLY_FAVORABLE",
            "原文含允許、可行或較有利的判斷標記；只表示在文本條件成立時可偏向順行，不代表無條件成功。",
        )
    if risk:
        return (
            "CONDITIONALLY_RISK_AWARE",
            "原文含危、悔、難等風險標記；只表示需要風險管理或條件修正，不可直接換成必敗。",
        )
    return (
        "OPEN_TEXT_REVIEW_REQUIRED",
        "原文未命中目前 judgment-marker ontology；必須直接讀爻辭與小象，不能把未命中當成無義。",
    )


def build_zhouyi_line_meaning_review(hexagram_number: int, line_number: int) -> dict[str, Any]:
    """Build a source-grounded, non-commentarial conditional review for one Zhouyi line.

    The review is deliberately project-level. It preserves the classical text as
    primary evidence and only organizes conditions, risk, phase and football
    hypotheses already supported by source-term retrieval. It never fabricates a
    classical commentary, probability, score or final result.
    """

    if line_number not in range(1, 7):
        raise ValueError("line_number 必須為 1..6")
    hexagram = zhouyi_hexagram(hexagram_number)
    line = hexagram["lines"][line_number - 1]
    profile = zhouyi_line_semantic_profile(line)
    role = _line_roles()[line_number]

    markers = profile.get("judgment_markers", [])
    marker_ids = {str(row["id"]) for row in markers}
    tendency, tendency_note = _conditional_tendency(marker_ids)
    matched_terms = _unique([term for row in markers for term in row.get("matched_terms", [])])
    abstractions = _unique([str(value) for value in profile.get("project_abstractions", [])])
    observables = _unique([str(value) for value in profile.get("observable_signals", [])])
    counters = _unique([str(value) for value in profile.get("counter_signals", [])])
    football_hypotheses = _unique([str(value) for value in profile.get("football_hypotheses", [])])

    text_conditions = [
        {
            "marker_id": row["id"],
            "matched_terms": list(row.get("matched_terms", [])),
            "project_note": row["project_note"],
        }
        for row in markers
    ]
    if not text_conditions:
        text_conditions.append(
            {
                "marker_id": "NO_JUDGMENT_MARKER_MATCH",
                "matched_terms": [],
                "project_note": "目前 ontology 未命中判斷字詞；回到完整原文，不生成替代性吉凶。",
            }
        )

    ambiguity: list[str] = []
    if marker_ids & FAVORABLE_MARKERS and marker_ids & RISK_MARKERS:
        ambiguity.append("同一爻同時存在允許／有利與風險標記，屬條件式張力。")
    if not profile.get("semantic_atoms"):
        ambiguity.append("目前 semantic ontology 沒有命中此爻的語義 atom；原文仍是主要證據。")
    xiaoxiang = line.get("xiaoxiang") or {}
    if xiaoxiang.get("status") != "MAPPED":
        ambiguity.append(f"小象狀態為 {xiaoxiang.get('status') or 'UNKNOWN'}；不得擅自補造逐爻小象。")

    football = {
        "authority": "PROJECT_REVIEW__NOT_CLASSICAL_COMMENTARY",
        "source_basis": {
            "line_classical_text": line.get("classical_text"),
            "xiaoxiang_classical_text": (
                xiaoxiang.get("classical_text") if xiaoxiang.get("status") == "MAPPED" else None
            ),
            "matched_judgment_terms": matched_terms,
            "semantic_atom_ids": [row.get("id") for row in profile.get("semantic_atoms", [])],
        },
        "abstract_meaning": abstractions or ["RAW_TEXT_REVIEW_REQUIRED"],
        "possible_scenario": football_hypotheses or ["沒有足夠 ontology 命中；不得為了足球 coverage 強造情境。"],
        "observable_signals": observables or ["需由實際賽前／賽中可觀察資料建立支持，不能只靠文字聯想。"],
        "counter_signals": counters or ["若實際場面沒有對應條件，應降低此 modern application 的解讀權重。"],
        "confidence_note": (
            "SOURCE_TERM_GROUNDED_PROJECT_REVIEW"
            if profile.get("semantic_atoms") or markers
            else "RAW_TEXT_ONLY__HUMAN_OR_CHATGPT_REVIEW_REQUIRED"
        ),
        "boundary": "足球情境是現代應用候選，不是《周易》原文中的足球公式，也不輸出勝率或固定比分。",
    }

    return {
        "schema_version": "stark-zhouyi-line-meaning-review-v1.0.0",
        "authority": "PROJECT_REVIEW__NOT_CLASSICAL_COMMENTARY",
        "hexagram": {
            "number": int(hexagram["number"]),
            "name": hexagram["name"],
            "symbol": hexagram["symbol"],
        },
        "line": {
            "number": line_number,
            "marker": line["marker"],
            "classical_text": line["classical_text"],
            "xiaoxiang": xiaoxiang,
            "source_page_start": line["source_page_start"],
            "source_file": hexagram["source"]["file"],
            "source_commit": hexagram["source"]["commit"],
        },
        "text_conditions": text_conditions,
        "action_boundary": {
            "phase": role["phase"],
            "project_general": role["general"],
            "rule": "爻位只提供相對階段與行動位置，不直接映射固定足球分鐘。",
        },
        "risk_boundary": {
            "risk_marker_ids": sorted(marker_ids & RISK_MARKERS),
            "rule": "風險字詞必須連同完整句法、體用旺衰與互變閱讀；不得把『危／悔／難』直接換成必敗。",
        },
        "turning_point": {
            "relative_phase": role["phase"],
            "interpretation": "此爻可作相對階段的條件式轉折審查，不是固定 match minute。",
        },
        "conditional_outcome_tendency": {
            "status": tendency,
            "note": tendency_note,
        },
        "misread_warnings": [
            "不得只取吉、凶、悔、吝、厲、无咎等單字代替完整原文。",
            "目前年月日時先天數法中，周易動爻屬 SUPPORTING review，不凌駕梅花體用旺衰與互變。",
            "不得把此爻直接換成主勝／客勝、統計機率或固定比分。",
        ],
        "ambiguity": ambiguity,
        "football": football,
        "boundary": "此 meaning_review 是來源約束的 JARVIS 專案審查物件，不是古典注疏或預測模型。",
    }


def zhouyi_line_meaning_review_audit() -> dict[str, Any]:
    reviews = [
        build_zhouyi_line_meaning_review(hexagram_number, line_number)
        for hexagram_number in range(1, 65)
        for line_number in range(1, 7)
    ]
    raw_text_only = sum(
        review["football"]["confidence_note"] == "RAW_TEXT_ONLY__HUMAN_OR_CHATGPT_REVIEW_REQUIRED"
        for review in reviews
    )
    mixed = sum(
        review["conditional_outcome_tendency"]["status"] == "MIXED_CONDITIONAL"
        for review in reviews
    )
    return {
        "schema_version": "stark-zhouyi-line-meaning-review-audit-v1.0.0",
        "total_reviews": len(reviews),
        "expected_reviews": 384,
        "raw_text_only_reviews": raw_text_only,
        "mixed_conditional_reviews": mixed,
        "authority": "PROJECT_REVIEW__NOT_CLASSICAL_COMMENTARY",
        "completion_rule": "384/384 皆有結構化 review；raw-text-only 仍算完整審查物件，但不得假裝具有 ontology 語義覆蓋。",
    }
