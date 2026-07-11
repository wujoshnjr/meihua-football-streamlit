from __future__ import annotations

from typing import Any, Mapping

from evaluation import (
    calibration_summary_from_row,
    evaluate_predictions,
    local_calibration_summary,
    normalize_score,
    outcome,
    score_tuple,
)
from models import AIAnalysis, RulePrediction


def _score_text(score: tuple[int, int]) -> str:
    return f"{score[0]}-{score[1]}"


def candidate_scores(rule_prediction: RulePrediction, limit: int = 15) -> list[tuple[int, int]]:
    ranked: list[tuple[int, int]] = []
    buckets: dict[str, list[tuple[int, int]]] = {"體方勝": [], "平局": [], "用方勝": []}
    for row in rule_prediction.score_grid:
        if not isinstance(row, Mapping):
            continue
        parsed = score_tuple(str(row.get("score", "")))
        if parsed is None or parsed in ranked:
            continue
        ranked.append(parsed)
        buckets[outcome(_score_text(parsed))].append(parsed)
    for score in rule_prediction.scores:
        if score not in ranked:
            ranked.append(score)
            buckets[outcome(_score_text(score))].append(score)

    selected: list[tuple[int, int]] = []
    for label in ["體方勝", "平局", "用方勝"]:
        for score in buckets[label][:4]:
            if score not in selected:
                selected.append(score)
    selected.sort(key=lambda score: ranked.index(score) if score in ranked else 999)
    for score in ranked:
        if score not in selected:
            selected.append(score)
        if len(selected) >= max(12, limit):
            break
    return selected[: max(12, limit)]


def _valid_ai_scores(ai_analysis: AIAnalysis, pool: list[tuple[int, int]]) -> list[tuple[int, int]]:
    output: list[tuple[int, int]] = []
    allowed = set(pool)
    for score in ai_analysis.scores:
        if score in allowed and score not in output:
            output.append(score)
    return output


def _strong_evidence(ai_analysis: AIAnalysis) -> bool:
    gap = abs(float(ai_analysis.body_strength_score) - float(ai_analysis.use_strength_score))
    return (
        float(ai_analysis.evidence_quality) >= 0.65
        and float(ai_analysis.direction_confidence) >= 0.65
        and gap >= 12.0
    )


def _fill_three(preferred: list[tuple[int, int]], pool: list[tuple[int, int]]) -> list[tuple[int, int]]:
    output: list[tuple[int, int]] = []
    for score in preferred + pool:
        if score not in output:
            output.append(score)
        if len(output) == 3:
            break
    return output


def controlled_final_scores(
    rule_prediction: RulePrediction,
    ai_analysis: AIAnalysis | None,
    similar_case_count: int = 0,
) -> tuple[list[tuple[int, int]], dict[str, Any]]:
    rule_scores = list(rule_prediction.scores[:3])
    pool = candidate_scores(rule_prediction, 15)
    metadata: dict[str, Any] = {
        "mode": "rule_only",
        "ai_weight": 0.0,
        "similar_case_count": int(similar_case_count),
        "direction_guard": False,
        "allowed_pool": [_score_text(score) for score in pool],
        "evidence_quality": 0.0,
        "direction_confidence": 0.0,
        "strength_gap": 0.0,
        "note": "未使用AI，採固定規則排序。",
    }
    if not ai_analysis or not ai_analysis.ok:
        return rule_scores, metadata

    ai_scores = _valid_ai_scores(ai_analysis, pool)
    if not ai_scores:
        metadata["note"] = "AI沒有提供平衡候選池內的有效比分，保留規則排序。"
        return rule_scores, metadata

    evidence_quality = max(0.0, min(1.0, float(ai_analysis.evidence_quality)))
    direction_confidence = max(0.0, min(1.0, float(ai_analysis.direction_confidence)))
    signed_gap = float(ai_analysis.body_strength_score) - float(ai_analysis.use_strength_score)
    strong = _strong_evidence(ai_analysis)
    rule_direction = outcome(_score_text(rule_scores[0])) if rule_scores else ""
    ai_direction = outcome(_score_text(ai_scores[0]))
    conflict = ai_direction != rule_direction

    # 強證據糾錯：候選仍必須在平衡池內，且AI首選原規則池順位不得低於第9名。
    if conflict and strong:
        eligible = [score for score in ai_scores if pool.index(score) <= 8]
        if eligible:
            final = _fill_three(eligible, pool)
            metadata.update(
                {
                    "mode": "strong_evidence_correction_v3.3",
                    "ai_weight": 0.55,
                    "evidence_quality": round(evidence_quality, 3),
                    "direction_confidence": round(direction_confidence, 3),
                    "strength_gap": round(signed_gap, 2),
                    "note": "足球證據品質、方向信心與實力差同時達標；允許AI在平衡候選池前9名內糾正規則方向。",
                }
            )
            return final, metadata

    if conflict and similar_case_count < 3 and not strong:
        metadata.update(
            {
                "mode": "direction_guard",
                "direction_guard": True,
                "evidence_quality": round(evidence_quality, 3),
                "direction_confidence": round(direction_confidence, 3),
                "strength_gap": round(signed_gap, 2),
                "note": "AI想改變方向，但案例與足球證據不足；保留規則首選。",
            }
        )
        return rule_scores, metadata

    case_component = min(0.16, max(0, similar_case_count) * 0.02)
    ai_weight = min(0.48, 0.12 + case_component + 0.16 * evidence_quality + 0.10 * direction_confidence)
    if conflict and not strong:
        ai_weight = min(ai_weight, 0.28)

    rule_rank = {score: index for index, score in enumerate(pool)}
    ai_rank = {score: index for index, score in enumerate(ai_scores)}
    max_shift = 6 if strong else 3
    preferred_outcome = "體方勝" if signed_gap >= 12 else ("用方勝" if signed_gap <= -12 else "")

    blended: list[tuple[tuple[int, int], float]] = []
    for score in pool:
        base_rank = rule_rank[score]
        requested_rank = ai_rank.get(score, base_rank)
        bounded_rank = max(base_rank - max_shift, min(base_rank + max_shift, requested_rank))
        blended_rank = (1.0 - ai_weight) * base_rank + ai_weight * bounded_rank
        if preferred_outcome and evidence_quality >= 0.60 and outcome(_score_text(score)) == preferred_outcome:
            blended_rank -= 0.75 * direction_confidence
        blended.append((score, blended_rank))
    blended.sort(key=lambda item: (item[1], rule_rank[item[0]]))
    final = [score for score, _ in blended[:3]]

    final_outcomes = {outcome(_score_text(score)) for score in final}
    if len(final_outcomes) == 1 and max(evidence_quality, direction_confidence) < 0.72:
        alternative = next((score for score, _ in blended[3:] if outcome(_score_text(score)) not in final_outcomes), None)
        if alternative is not None:
            final[-1] = alternative

    metadata.update(
        {
            "mode": "evidence_ensemble_v3.3",
            "ai_weight": round(ai_weight, 4),
            "evidence_quality": round(evidence_quality, 3),
            "direction_confidence": round(direction_confidence, 3),
            "strength_gap": round(signed_gap, 2),
            "note": "AI在勝平負平衡候選池內重排；弱證據不能翻盤，強證據可受控糾錯。",
        }
    )
    return final, metadata


def final_scores(
    rule_prediction: RulePrediction,
    ai_analysis: AIAnalysis | None,
    similar_case_count: int = 0,
) -> list[tuple[int, int]]:
    return controlled_final_scores(rule_prediction, ai_analysis, similar_case_count)[0]


__all__ = [
    "normalize_score",
    "score_tuple",
    "outcome",
    "evaluate_predictions",
    "candidate_scores",
    "controlled_final_scores",
    "final_scores",
    "local_calibration_summary",
    "calibration_summary_from_row",
]
