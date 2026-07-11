from __future__ import annotations

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
        }

    actual_text = _score_text(actual)
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
    }


def candidate_scores(rule_prediction: RulePrediction, limit: int = 12) -> list[tuple[int, int]]:
    candidates: list[tuple[int, int]] = []
    for row in rule_prediction.score_grid[: max(3, limit)]:
        if not isinstance(row, Mapping):
            continue
        parsed = score_tuple(str(row.get("score", "")))
        if parsed is not None and parsed not in candidates:
            candidates.append(parsed)
    for score in rule_prediction.scores:
        if score not in candidates:
            candidates.append(score)
    return candidates[: max(3, limit)]


def controlled_final_scores(
    rule_prediction: RulePrediction,
    ai_analysis: AIAnalysis | None,
    similar_case_count: int = 0,
) -> tuple[list[tuple[int, int]], dict[str, Any]]:
    """以規則候選池限制 AI，只允許有限重排，不准任意創造比分。"""
    if similar_case_count <= 0 and ai_analysis and ai_analysis.used_case_ids:
        similar_case_count = len(ai_analysis.used_case_ids)
    rule_scores = list(rule_prediction.scores[:3])
    pool = candidate_scores(rule_prediction, 12)
    metadata: dict[str, Any] = {
        "mode": "rule_only",
        "ai_weight": 0.0,
        "similar_case_count": int(similar_case_count),
        "direction_guard": False,
        "allowed_pool": [_score_text(score) for score in pool],
        "note": "未使用AI，採固定規則排序。",
    }
    if not ai_analysis or not ai_analysis.ok:
        return rule_scores, metadata

    ai_scores = [score for score in _parse_scores(ai_analysis.scores) if score in pool]
    if not ai_scores:
        metadata["note"] = "AI沒有提供規則候選池內的有效比分，保留固定規則排序。"
        return rule_scores, metadata

    rule_first_outcome = outcome(_score_text(rule_scores[0])) if rule_scores else ""
    ai_first_outcome = outcome(_score_text(ai_scores[0]))
    if similar_case_count < 3 and ai_first_outcome != rule_first_outcome:
        metadata.update(
            {
                "mode": "direction_guard",
                "direction_guard": True,
                "note": "已確認相似案例少於3場，AI不得推翻固定規則的勝平負方向。",
            }
        )
        return rule_scores, metadata

    if similar_case_count < 3:
        ai_weight = 0.20
    elif similar_case_count <= 10:
        ai_weight = 0.35
    else:
        ai_weight = 0.45

    rule_rank = {score: index for index, score in enumerate(pool)}
    ai_rank = {score: index for index, score in enumerate(ai_scores)}
    blended: list[tuple[tuple[int, int], float]] = []
    for score in pool:
        base_rank = rule_rank[score]
        requested_rank = ai_rank.get(score, base_rank)
        bounded_rank = max(base_rank - 3, min(base_rank + 3, requested_rank))
        blended_rank = (1.0 - ai_weight) * base_rank + ai_weight * bounded_rank
        blended.append((score, blended_rank))
    blended.sort(key=lambda item: (item[1], rule_rank[item[0]]))
    final = [score for score, _ in blended[:3]]

    if similar_case_count < 3 and rule_scores:
        final = [rule_scores[0]] + [score for score in final if score != rule_scores[0]]
        for score in rule_scores[1:]:
            if len(final) >= 3:
                break
            if score not in final:
                final.append(score)
        final = final[:3]

    metadata.update(
        {
            "mode": "controlled_ai_reorder",
            "ai_weight": ai_weight,
            "note": "AI只在規則前12名候選內有限重排，單一比分最多移動3個順位。",
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
        status = "首選的勝平負方向與實際結果不同，需重新檢查體用與本互變權重。"

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
        f"變卦{result.changed_hexagram}。下次應優先檢查『{result.relation}』是否讓某方進球被錯誤放大或壓低，"
        "並把校準寫成可泛化的結構教訓，而不是固定某卦等於某比分。"
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
