from __future__ import annotations

from typing import Any

from meihua.engine import MeihuaSnapshot


RELATION_CLASS = {
    "生體": "EXTERNAL_ASSISTS_BODY",
    "體生用": "BODY_EXPENDS_OUTWARD",
    "克體": "EXTERNAL_CONSTRAINS_BODY",
    "體克用": "BODY_CONSTRAINS_EXTERNAL",
    "比和": "PARITY_SAME_ELEMENT",
}

FAVORABLE_MARKERS = {"auspicious", "favorable_action", "success_flow", "no_blame"}
RISK_MARKERS = {"danger", "regret", "difficulty"}


def _relation_signal(layer: str, stage: str, trigram: str, relation: str) -> dict[str, str]:
    return {
        "layer": layer,
        "relative_stage": stage,
        "trigram": trigram,
        "relation_to_body": relation,
        "neutral_class": RELATION_CLASS[relation],
    }


def build_meihua_review_summary(
    snapshot: MeihuaSnapshot,
    *,
    method_audit: dict[str, Any],
    zhouyi_review: dict[str, Any],
    yilin_bridge: dict[str, Any],
) -> dict[str, Any]:
    """Build source-aware review registers without making the final divination judgment."""

    relation_signals = [
        _relation_signal("original_use", "immediate", snapshot.use_trigram, snapshot.body_use_relation),
        _relation_signal("mutual_upper", "middle", snapshot.mutual_upper_trigram, snapshot.mutual_upper_relation_to_body),
        _relation_signal("mutual_lower", "middle", snapshot.mutual_lower_trigram, snapshot.mutual_lower_relation_to_body),
        _relation_signal("changed_use", "late", snapshot.changed_use_trigram, snapshot.changed_use_relation_to_body),
    ]

    contradiction_register: list[dict[str, Any]] = []
    relation_classes = list(dict.fromkeys(row["neutral_class"] for row in relation_signals))
    if len(relation_classes) > 1:
        contradiction_register.append(
            {
                "id": "MIXED_BODY_USE_NETWORK",
                "type": "STRUCTURAL_TENSION",
                "claim_a": relation_signals[0],
                "claim_b": relation_signals[-1],
                "why_tension_exists": "本用、互層與變用對體的五行作用並非單一同向類型。",
                "resolution_rule": "保留各層相對先後與體旺衰，由 ChatGPT 合參；不得用單一 relation 覆蓋其他層。",
                "all_relation_classes": relation_classes,
            }
        )

    moving_profile = zhouyi_review["moving_line"]["semantic_profile"]
    marker_ids = {row["id"] for row in moving_profile.get("judgment_markers", [])}
    favorable_hits = sorted(marker_ids & FAVORABLE_MARKERS)
    risk_hits = sorted(marker_ids & RISK_MARKERS)
    if favorable_hits and risk_hits:
        contradiction_register.append(
            {
                "id": "MOVING_LINE_MIXED_JUDGMENT_MARKERS",
                "type": "TEXTUAL_CONDITION_TENSION",
                "claim_a": {"marker_family": "favorable_or_permissive", "hits": favorable_hits},
                "claim_b": {"marker_family": "risk_or_regret", "hits": risk_hits},
                "why_tension_exists": "同一動爻文本同時命中允許／有利與風險／悔吝語氣，不能抽單字斷定。",
                "resolution_rule": "回到完整爻辭上下文，並依本次 XIANTIAN_NUMBER_METHOD 把爻辭保持為 supporting review。",
            }
        )

    uncertainty_register = [
        {
            "id": "EXTERNAL_RESPONSES_NOT_RECORDED",
            "unknown": "三要、十應與其他外應未由目前 UI 在占測當時記錄。",
            "impact": "無法用古法外應層驗證或修正內卦，只能依 deterministic 卦象與已存原典。",
            "what_would_reduce_uncertainty": "未來加入帶 timestamp/provenance 的事前三要十應輸入與鎖定。",
        },
        {
            "id": "MULTI_EDITION_COLLATION_INCOMPLETE",
            "unknown": "固定《周易》與《焦氏易林》數位底本並不等於所有歷代版本、異文與注家已完成校勘。",
            "impact": "少數字詞或版本差異仍需人工文本學審查。",
            "what_would_reduce_uncertainty": "加入版本異文層並逐條記錄 collation status；原文層不可由 AI 自行補改。",
        },
        {
            "id": "MODERN_FOOTBALL_MAPPING_IS_HEURISTIC",
            "unknown": "古典象義到現代足球情境的映射不是古籍原有公式。",
            "impact": "只能作候選觀察鏡頭，不能等同統計勝率或必然事件。",
            "what_would_reduce_uncertainty": "保留 source basis、observable、counter-signal，並以事前資料驗證候選情境是否真的出現。",
        },
    ]

    source_coverage_audit = {
        "method_audit_ready": method_audit.get("status") == "METHOD_AWARE_REVIEW_READY",
        "method_class": method_audit["method"]["class"],
        "zhouyi_role": method_audit["weighting_decision"]["zhouyi_role"],
        "zhouyi_core_alignments_match": bool(zhouyi_review["source_audit"]["all_core_alignments_match"]),
        "zhouyi_moving_line_source_present": bool(zhouyi_review["moving_line"].get("classical_text")),
        "yilin_pair_materialized": yilin_bridge.get("status") == "MATERIALIZED",
        "yilin_lookup_key": yilin_bridge.get("lookup_key"),
        "external_response_status": method_audit["external_response_audit"]["source_lock"],
    }

    return {
        "kind": "meihua_deep_review_summary",
        "schema_version": "stark-meihua-deep-review-summary-v1.0.0",
        "status": "READY_WITH_DECLARED_GAPS",
        "method_weighting": {
            "method_class": method_audit["method"]["class"],
            "zhouyi_role": method_audit["weighting_decision"]["zhouyi_role"],
            "rule": method_audit["weighting_decision"]["zhouyi_rule"],
        },
        "relation_signals": relation_signals,
        "contradiction_register": contradiction_register,
        "uncertainty_register": uncertainty_register,
        "source_coverage_audit": source_coverage_audit,
        "handoff_rule": "ChatGPT 必須先讀 method weighting，再讀 relation signals、原典、易林、矛盾與不確定性；JARVIS 不在此輸出最後吉凶、勝率或固定比分。",
    }
