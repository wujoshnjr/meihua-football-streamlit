from __future__ import annotations

import re
from typing import Any

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


def evaluate_predictions(scores: list[tuple[int, int]], actual_score: str) -> dict[str, Any]:
    actual = score_tuple(actual_score)
    score_texts = [f"{a}-{b}" for a, b in scores]
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
        }

    actual_text = f"{actual[0]}-{actual[1]}"
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
    }


def local_calibration_summary(
    result: HexagramResult,
    rule_prediction: RulePrediction,
    actual_score: str,
) -> str:
    actual = score_tuple(actual_score)
    if actual is None:
        return "賽前初判，尚未賽後校準；待賽後依實際90分鐘比分回填命中、偏差與卦象修正原因。"
    first = rule_prediction.scores[0]
    first_text = f"{first[0]}-{first[1]}"
    actual_text = f"{actual[0]}-{actual[1]}"
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

    lesson = (
        f"原判{first_text}，實際{actual_text}。{status}偏差：{'、'.join(errors)}。"
        f"本卦{result.main_hexagram}、互卦{result.mutual_hexagram}、{result.moving_line}爻在{result.moving_side}、"
        f"變卦{result.changed_hexagram}。下次應優先檢查「{result.relation}」是否讓某方進球被錯誤放大或壓低，"
        "並把校準寫成可泛化的結構教訓，而不是固定某卦等於某比分。"
    )
    return lesson


def final_scores(rule_prediction: RulePrediction, ai_analysis: AIAnalysis | None) -> list[tuple[int, int]]:
    if ai_analysis and ai_analysis.ok and len(ai_analysis.scores) >= 3:
        return ai_analysis.scores[:3]
    return rule_prediction.scores[:3]
