from __future__ import annotations

import math
import re
from typing import Any, Iterable, Mapping

from models import AIAnalysis, HexagramResult, RulePrediction


SCORE_PATTERN = re.compile(r"(?<!\d)(\d{1,2})\s*[-:：–—]\s*(\d{1,2})(?!\d)")


def normalize_score(value: str) -> str:
    match = SCORE_PATTERN.search(str(value or "").strip())
    if not match:
        return ""
    body, use = int(match.group(1)), int(match.group(2))
    if body > 20 or use > 20:
        return ""
    return f"{body}-{use}"


def score_tuple(value: str) -> tuple[int, int] | None:
    normalized = normalize_score(value)
    if not normalized:
        return None
    body, use = normalized.split("-")
    return int(body), int(use)


def outcome(value: str) -> str:
    score = score_tuple(value)
    if score is None:
        return ""
    if score[0] > score[1]:
        return "體方勝"
    if score[0] < score[1]:
        return "用方勝"
    return "平局"


def _score_text(score: tuple[int, int]) -> str:
    return f"{score[0]}-{score[1]}"


def _parse_scores(values: Iterable[Any]) -> list[tuple[int, int]]:
    output: list[tuple[int, int]] = []
    for value in values:
        if isinstance(value, (tuple, list)) and len(value) == 2:
            try:
                score = (int(value[0]), int(value[1]))
            except (TypeError, ValueError):
                continue
        else:
            parsed = score_tuple(str(value or ""))
            if parsed is None:
                continue
            score = parsed
        if score not in output:
            output.append(score)
    return output


def evaluate_predictions(scores: list[tuple[int, int]], actual_score: str) -> dict[str, Any]:
    actual = score_tuple(actual_score)
    score_texts = [_score_text(score) for score in scores]
    if actual is None:
        return {
            "actual_score": "",
            "first_hit": "",
            "second_hit": "",
            "third_hit": "",
            "any_hit": "",
            "first_outcome": outcome(score_texts[0]) if score_texts else "",
            "actual_outcome": "",
            "outcome_hit": "",
            "first_total_goal_error": "",
            "body_goal_error": "",
            "use_goal_error": "",
            "first_score_distance": "",
            "btts_hit": "",
            "over_2_5_hit": "",
        }

    actual_text = _score_text(actual)
    if not scores:
        return {
            "actual_score": actual_text,
            "first_hit": "",
            "second_hit": "",
            "third_hit": "",
            "any_hit": "",
            "first_outcome": "",
            "actual_outcome": outcome(actual_text),
            "outcome_hit": "",
            "first_total_goal_error": "",
            "body_goal_error": "",
            "use_goal_error": "",
            "first_score_distance": "",
            "btts_hit": "",
            "over_2_5_hit": "",
        }

    hits = ["是" if text == actual_text else "否" for text in score_texts[:3]]
    while len(hits) < 3:
        hits.append("否")
    first = scores[0] if scores else (0, 0)
    first_outcome = outcome(score_texts[0]) if score_texts else ""
    actual_outcome = outcome(actual_text)
    return {
        "actual_score": actual_text,
        "first_hit": hits[0],
        "second_hit": hits[1],
        "third_hit": hits[2],
        "any_hit": "是" if "是" in hits else "否",
        "first_outcome": first_outcome,
        "actual_outcome": actual_outcome,
        "outcome_hit": "是" if first_outcome == actual_outcome else "否",
        "first_total_goal_error": abs((first[0] + first[1]) - (actual[0] + actual[1])),
        "body_goal_error": first[0] - actual[0],
        "use_goal_error": first[1] - actual[1],
        "first_score_distance": abs(first[0] - actual[0]) + abs(first[1] - actual[1]),
        "btts_hit": "是" if (first[0] > 0 and first[1] > 0) == (actual[0] > 0 and actual[1] > 0) else "否",
        "over_2_5_hit": "是" if (sum(first) >= 3) == (sum(actual) >= 3) else "否",
    }


def outcome_brier(probabilities: Mapping[str, Any], actual_score: str) -> float | None:
    actual = outcome(actual_score)
    if not actual:
        return None
    labels = ["體方勝", "平局", "用方勝"]
    values: list[float] = []
    for label in labels:
        try:
            value = float(probabilities.get(label, 0.0))
        except (TypeError, ValueError):
            value = 0.0
        values.append(max(0.0, min(1.0, value)))
    total = sum(values)
    if total <= 0.0:
        return None
    normalized = [value / total for value in values]
    return sum(
        (probability - (1.0 if label == actual else 0.0)) ** 2
        for label, probability in zip(labels, normalized)
    )


def outcome_log_loss(probabilities: Mapping[str, Any], actual_score: str) -> float | None:
    actual = outcome(actual_score)
    if not actual:
        return None
    values: dict[str, float] = {}
    for label in ["體方勝", "平局", "用方勝"]:
        try:
            values[label] = max(0.0, min(1.0, float(probabilities.get(label, 0.0))))
        except (TypeError, ValueError):
            values[label] = 0.0
    total = sum(values.values())
    if total <= 0.0:
        return None
    return -math.log(max(1e-12, values[actual] / total))


def candidate_scores(rule_prediction: RulePrediction, limit: int = 15) -> list[tuple[int, int]]:
    """建立勝、平、負都有代表的候選池，避免錯誤規則把AI鎖死在單一方向。"""
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

    # 每個方向至少保留4個候選；其餘按原始規則順位補滿。
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


def _strong_ai_evidence(ai_analysis: AIAnalysis) -> bool:
    strength_gap = abs(float(ai_analysis.body_strength_score) - float(ai_analysis.use_strength_score))
    return (
        float(ai_analysis.evidence_quality) >= 0.65
        and float(ai_analysis.direction_confidence) >= 0.65
        and strength_gap >= 12.0
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
    """規則、足球先驗、卦象證據與案例共同決策；AI不能憑一句話任意翻盤。"""
    if similar_case_count <= 0 and ai_analysis and ai_analysis.used_case_ids:
        similar_case_count = len(ai_analysis.used_case_ids)

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

    ai_scores = [score for score in _parse_scores(ai_analysis.scores) if score in pool]
    if not ai_scores:
        metadata["note"] = "AI沒有提供平衡候選池內的有效比分，保留固定規則排序。"
        return rule_scores, metadata

    evidence_quality = max(0.0, min(1.0, float(ai_analysis.evidence_quality)))
    direction_confidence = max(0.0, min(1.0, float(ai_analysis.direction_confidence)))
    strength_gap_signed = float(ai_analysis.body_strength_score) - float(ai_analysis.use_strength_score)
    strong_evidence = _strong_ai_evidence(ai_analysis)

    rule_first_outcome = outcome(_score_text(rule_scores[0])) if rule_scores else ""
    ai_first_outcome = outcome(_score_text(ai_scores[0]))
    direction_conflict = ai_first_outcome != rule_first_outcome

    # Strong correction remains bounded to the rule engine's first nine balanced
    # candidates. AI cannot invent a score or escape the football/hexagram grid.
    if direction_conflict and strong_evidence:
        eligible = [score for score in ai_scores if pool.index(score) <= 8]
        if eligible:
            final = _fill_three(eligible, pool)
            metadata.update(
                {
                    "mode": "strong_evidence_correction_v4",
                    "ai_weight": 0.55,
                    "evidence_quality": round(evidence_quality, 3),
                    "direction_confidence": round(direction_confidence, 3),
                    "strength_gap": round(strength_gap_signed, 2),
                    "note": (
                        "足球證據品質、方向信心與實力差同時達標；"
                        "允許AI在足球先驗×有界卦象候選池前9名內糾正方向。"
                    ),
                }
            )
            return final, metadata

    # 案例少時仍可糾正規則，但必須同時有高品質足球證據、方向信心與明顯實力差。
    if direction_conflict and similar_case_count < 3 and not strong_evidence:
        metadata.update(
            {
                "mode": "direction_guard",
                "direction_guard": True,
                "evidence_quality": evidence_quality,
                "direction_confidence": direction_confidence,
                "strength_gap": round(strength_gap_signed, 2),
                "note": "AI想改變勝平負方向，但案例與足球證據不足；保留規則首選並只顯示矛盾提醒。",
            }
        )
        return rule_scores, metadata

    case_component = min(0.16, max(0, similar_case_count) * 0.02)
    evidence_component = 0.16 * evidence_quality
    direction_component = 0.10 * direction_confidence
    ai_weight = min(0.48, 0.12 + case_component + evidence_component + direction_component)
    if direction_conflict and not strong_evidence:
        ai_weight = min(ai_weight, 0.28)

    rule_rank = {score: index for index, score in enumerate(pool)}
    ai_rank = {score: index for index, score in enumerate(ai_scores)}
    max_shift = 6 if strong_evidence else 3
    preferred_outcome = "體方勝" if strength_gap_signed >= 12 else ("用方勝" if strength_gap_signed <= -12 else "")

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

    # 若整體證據不強，前三選至少保留兩種方向，避免再次出現三個比分全押同一邊。
    final_outcomes = {outcome(_score_text(score)) for score in final}
    if len(final_outcomes) == 1 and max(evidence_quality, direction_confidence) < 0.72:
        alternative = next(
            (score for score, _ in blended[3:] if outcome(_score_text(score)) not in final_outcomes),
            None,
        )
        if alternative is not None:
            final[-1] = alternative

    metadata.update(
        {
            "mode": "evidence_ensemble_v4",
            "ai_weight": round(ai_weight, 4),
            "direction_guard": False,
            "evidence_quality": round(evidence_quality, 3),
            "direction_confidence": round(direction_confidence, 3),
            "strength_gap": round(strength_gap_signed, 2),
            "note": (
                "AI只在足球先驗×有界卦象產生的勝平負平衡候選池內重排；一般最多移動3位，"
                "只有高品質足球證據、方向信心與明顯實力差同時成立時才可移動6位並糾正規則方向。"
            ),
        }
    )
    return final, metadata


def final_scores(
    rule_prediction: RulePrediction,
    ai_analysis: AIAnalysis | None,
    similar_case_count: int = 0,
) -> list[tuple[int, int]]:
    scores, _ = controlled_final_scores(rule_prediction, ai_analysis, similar_case_count)
    return scores


def local_calibration_summary(
    result: HexagramResult,
    rule_prediction: RulePrediction,
    actual_score: str,
) -> str:
    actual = score_tuple(actual_score)
    if actual is None:
        return "賽前初判，尚未賽後校準；待賽後依實際90分鐘比分回填命中、偏差與卦象修正原因。"
    first = rule_prediction.scores[0]
    first_text = _score_text(first)
    actual_text = _score_text(actual)
    direction_hit = outcome(first_text) == outcome(actual_text)
    exact_hit = first == actual

    if exact_hit:
        status = "首選比分命中，保留本場整體卦勢鏈的排序邏輯。"
    elif direction_hit:
        status = "勝平負方向命中，但精確比分未命中。"
    else:
        status = "首選的勝平負方向與實際結果不同，需重新檢查體用、足球先驗與本互變權重。"

    body_error = first[0] - actual[0]
    use_error = first[1] - actual[1]
    errors: list[str] = []
    if body_error > 0:
        errors.append(f"體方進球高估{body_error}球")
    elif body_error < 0:
        errors.append(f"體方進球低估{abs(body_error)}球")
    if use_error > 0:
        errors.append(f"用方進球高估{use_error}球")
    elif use_error < 0:
        errors.append(f"用方進球低估{abs(use_error)}球")
    if not errors:
        errors.append("雙方進球數均吻合")

    return (
        f"原判{first_text}，實際{actual_text}。{status}偏差：{'、'.join(errors)}。"
        f"本卦{result.main_hexagram}、互卦{result.mutual_hexagram}、{result.moving_line}爻在{result.moving_side}、"
        f"變卦{result.changed_hexagram}。下次應分開檢查足球先驗、體用風險、前中後段轉象與比分候選池，"
        "不可把任何單一生剋關係直接寫成固定勝負。"
    )


def calibration_summary_from_row(row: Mapping[str, Any], actual_score: str) -> str:
    actual = normalize_score(actual_score)
    first = normalize_score(
        str(
            row.get("最終首選比分")
            or row.get("AI首選比分")
            or row.get("規則首選比分")
            or row.get("首選比分")
            or ""
        )
    )
    if not actual:
        return "尚未輸入有效的90分鐘實際比分。"
    if not first:
        return f"實際比分{actual}；舊案例缺少首選比分，需人工補充預測紀錄後再做完整校準。"
    first_tuple = score_tuple(first) or (0, 0)
    actual_tuple = score_tuple(actual) or (0, 0)
    exact = first == actual
    direction_hit = outcome(first) == outcome(actual)
    if exact:
        status = "首選精確命中。"
    elif direction_hit:
        status = "勝平負方向命中，但精確比分未中。"
    else:
        status = "勝平負方向未命中。"
    body_error = first_tuple[0] - actual_tuple[0]
    use_error = first_tuple[1] - actual_tuple[1]
    return (
        f"原鎖定首選{first}，實際{actual}。{status}"
        f"體方進球誤差{body_error:+d}，用方進球誤差{use_error:+d}。"
        f"卦勢鏈：本卦{row.get('本卦', '')}、互卦{row.get('互卦', '')}、"
        f"{row.get('動爻', '')}爻在{row.get('動爻位置', '')}、變卦{row.get('變卦', '')}。"
    )
