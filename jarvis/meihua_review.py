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


def _unique_strings(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def _build_cross_system_coherence(
    *,
    zhouyi_review: dict[str, Any],
    yilin_bridge: dict[str, Any],
) -> dict[str, Any]:
    """Compare only source alignment and project semantic lenses, never final divinatory outcome."""

    moving = zhouyi_review["moving_line"]
    zhouyi_profile = moving.get("semantic_profile") or {}
    yilin_profile = yilin_bridge.get("semantic_profile") or {}

    zhouyi_domains = _unique_strings([str(value) for value in zhouyi_profile.get("domains", [])])
    yilin_domains = _unique_strings([str(value) for value in yilin_profile.get("domains", [])])
    shared_domains = sorted(set(zhouyi_domains) & set(yilin_domains))
    zhouyi_only = sorted(set(zhouyi_domains) - set(yilin_domains))
    yilin_only = sorted(set(yilin_domains) - set(zhouyi_domains))

    original = zhouyi_review["original"]
    changed = zhouyi_review["changed"]
    yilin_from = yilin_bridge.get("from_hexagram") or {}
    yilin_to = yilin_bridge.get("to_hexagram") or {}
    pair_alignment = {
        "from_number_matches_original": int(yilin_from.get("number", -1)) == int(original["number"]),
        "from_name_matches_original": yilin_from.get("name") == original["name"],
        "to_number_matches_changed": int(yilin_to.get("number", -1)) == int(changed["number"]),
        "to_name_matches_changed": yilin_to.get("name") == changed["name"],
    }
    pair_alignment["all_match"] = all(pair_alignment.values())

    reinforcement: list[dict[str, Any]] = []
    if shared_domains:
        reinforcement.append(
            {
                "id": "SHARED_PROJECT_SEMANTIC_DOMAINS",
                "status": "PROJECT_HEURISTIC_REINFORCEMENT",
                "shared_domains": shared_domains,
                "source_basis": {
                    "zhouyi": {
                        "moving_line": moving.get("marker"),
                        "classical_text": moving.get("classical_text"),
                        "semantic_atom_ids": [row.get("id") for row in zhouyi_profile.get("semantic_atoms", [])],
                    },
                    "yilin": {
                        "lookup_key": yilin_bridge.get("lookup_key"),
                        "classical_text": (yilin_bridge.get("classical_entry") or {}).get("classical_text"),
                        "image_atom_ids": [row.get("id") for row in yilin_profile.get("image_atoms", [])],
                    },
                },
                "meaning": "周易動爻與焦氏易林的專案語義召回命中共同領域，可作同題候選觀察鏡頭；不等於古籍彼此互證或結果同向。",
            }
        )

    independent_signal: list[dict[str, Any]] = []
    if zhouyi_only:
        independent_signal.append(
            {
                "id": "ZHOUYI_ONLY_DOMAINS",
                "domains": zhouyi_only,
                "meaning": "這些專案語義只由周易動爻文本召回，焦氏易林本→變條目未命中同領域；應保留為獨立訊號。",
            }
        )
    if yilin_only:
        independent_signal.append(
            {
                "id": "YILIN_ONLY_DOMAINS",
                "domains": yilin_only,
                "meaning": "這些專案語義只由焦氏易林本→變林辭召回，周易動爻未命中同領域；應保留為獨立情境補充。",
            }
        )

    if not shared_domains:
        coherence_status = "NO_SHARED_PROJECT_DOMAIN__READ_TEXTS_INDEPENDENTLY"
    else:
        coherence_status = "SHARED_PROJECT_DOMAIN__CONDITIONAL_REINFORCEMENT"

    return {
        "schema_version": "stark-meihua-cross-system-coherence-v1.0.0",
        "status": coherence_status,
        "source_pair_alignment": pair_alignment,
        "zhouyi": {
            "role": "SUPPORTING_FOR_CURRENT_XIANTIAN_NUMBER_METHOD",
            "moving_line": moving.get("marker"),
            "domains": zhouyi_domains,
            "judgment_marker_ids": [row.get("id") for row in zhouyi_profile.get("judgment_markers", [])],
        },
        "yilin": {
            "role": "TRANSFORMATION_CONTEXT__DOES_NOT_RECAST",
            "lookup_key": yilin_bridge.get("lookup_key"),
            "domains": yilin_domains,
            "semantic_status": yilin_profile.get("status"),
        },
        "reinforcement": reinforcement,
        "tension": [],
        "independent_signal": independent_signal,
        "shared_domains": shared_domains,
        "interpretation_rule": (
            "共同 domain 只代表兩個 PROJECT_HEURISTIC 召回層具有可比較語義，不是古典注解互證、吉凶投票或統計權重。"
            "若沒有共同 domain，ChatGPT 應直接分讀兩段古文；若來源 pair 對齊失敗，應停止跨系統合參並先修資料鏈。"
        ),
    }


def build_meihua_review_summary(
    snapshot: MeihuaSnapshot,
    *,
    method_audit: dict[str, Any],
    zhouyi_review: dict[str, Any],
    yilin_bridge: dict[str, Any],
    temporal_precision_audit: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build source-aware review registers without making the final divination judgment."""

    relation_signals = [
        _relation_signal("original_use", "immediate", snapshot.use_trigram, snapshot.body_use_relation),
        _relation_signal("mutual_upper", "middle", snapshot.mutual_upper_trigram, snapshot.mutual_upper_relation_to_body),
        _relation_signal("mutual_lower", "middle", snapshot.mutual_lower_trigram, snapshot.mutual_lower_relation_to_body),
        _relation_signal("changed_use", "late", snapshot.changed_use_trigram, snapshot.changed_use_relation_to_body),
    ]
    cross_system_coherence = _build_cross_system_coherence(
        zhouyi_review=zhouyi_review,
        yilin_bridge=yilin_bridge,
    )

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

    if not cross_system_coherence["source_pair_alignment"]["all_match"]:
        contradiction_register.append(
            {
                "id": "YILIN_TRANSFORMATION_SOURCE_MISMATCH",
                "type": "SOURCE_INTEGRITY_CONFLICT",
                "claim_a": {
                    "zhouyi_original": zhouyi_review["original"]["name"],
                    "zhouyi_changed": zhouyi_review["changed"]["name"],
                },
                "claim_b": {
                    "yilin_from": (yilin_bridge.get("from_hexagram") or {}).get("name"),
                    "yilin_to": (yilin_bridge.get("to_hexagram") or {}).get("name"),
                },
                "why_tension_exists": "焦氏易林 bridge 的本卦→之卦與周易審查層的本卦→變卦來源鍵不一致。",
                "resolution_rule": "停止易林跨系統合參並修復 deterministic lookup／catalog alignment；不得由 AI 猜測正確 pair。",
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
    if not cross_system_coherence["shared_domains"]:
        uncertainty_register.append(
            {
                "id": "NO_SHARED_ZHOUYI_YILIN_PROJECT_DOMAIN",
                "unknown": "周易動爻與焦氏易林林辭目前沒有命中共同的專案語義 domain。",
                "impact": "不能用 ontology 相交宣稱兩者同向；兩段原文應保持獨立閱讀。",
                "what_would_reduce_uncertainty": "人工逐字審查兩段原文，或日後擴充有來源邊界的 semantic ontology；不得為了提高 coverage 強配語義。",
            }
        )

    temporal_context = None
    if temporal_precision_audit:
        summary = temporal_precision_audit["boundary_summary"]
        temporal_context = {
            "status": temporal_precision_audit["status"],
            "horizon_minutes": temporal_precision_audit["analysis_window"]["horizon_minutes"],
            "hour_branch_changes": summary["hour_branch_changes"],
            "calendar_changes": summary["calendar_changes"],
            "utc_offset_changes": summary["utc_offset_changes"],
            "boundary_count": summary["total_boundary_events"],
            "authority": "SECONDARY_TEMPORAL_CONTEXT_ONLY",
        }
        if summary["hour_branch_changes"] or summary["calendar_changes"] or summary["utc_offset_changes"]:
            uncertainty_register.append(
                {
                    "id": "MATCH_CLOCK_PHASE_AT_TEMPORAL_BOUNDARY_UNVERIFIED",
                    "unknown": "事件期間存在時支／日界／時區交界，但目前 packet 沒有逐事件官方 match-clock timeline。",
                    "impact": "可以精確知道交界距開賽多少真實分鐘，卻不能僅憑 wall-clock 保證當時是上半場、半場、傷停、下半場或延長賽。",
                    "what_would_reduce_uncertainty": "加入實際半場結束、下半場開始、VAR/延誤、正規時間結束與延長賽開始等 timestamped match-clock events。",
                }
            )

    source_coverage_audit = {
        "method_audit_ready": method_audit.get("status") == "METHOD_AWARE_REVIEW_READY",
        "method_class": method_audit["method"]["class"],
        "zhouyi_role": method_audit["weighting_decision"]["zhouyi_role"],
        "zhouyi_core_alignments_match": bool(zhouyi_review["source_audit"]["all_core_alignments_match"]),
        "zhouyi_moving_line_source_present": bool(zhouyi_review["moving_line"].get("classical_text")),
        "yilin_pair_materialized": yilin_bridge.get("status") == "MATERIALIZED",
        "yilin_lookup_key": yilin_bridge.get("lookup_key"),
        "yilin_pair_matches_zhouyi_original_changed": cross_system_coherence["source_pair_alignment"]["all_match"],
        "external_response_status": method_audit["external_response_audit"]["source_lock"],
        "temporal_precision_audit_ready": (
            temporal_precision_audit is None
            or temporal_precision_audit.get("status") == "TEMPORAL_BOUNDARY_AUDIT_READY"
        ),
    }

    return {
        "kind": "meihua_deep_review_summary",
        "schema_version": "stark-meihua-deep-review-summary-v1.1.0",
        "status": "READY_WITH_DECLARED_GAPS",
        "method_weighting": {
            "method_class": method_audit["method"]["class"],
            "zhouyi_role": method_audit["weighting_decision"]["zhouyi_role"],
            "rule": method_audit["weighting_decision"]["zhouyi_rule"],
        },
        "relation_signals": relation_signals,
        "temporal_context": temporal_context,
        "cross_system_coherence": cross_system_coherence,
        "contradiction_register": contradiction_register,
        "uncertainty_register": uncertainty_register,
        "source_coverage_audit": source_coverage_audit,
        "handoff_rule": "ChatGPT 必須先讀 method weighting，再讀 relation signals、temporal context、cross_system_coherence、原典、易林、矛盾與不確定性；JARVIS 不在此輸出最後吉凶、勝率或固定比分。",
    }
