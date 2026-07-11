from __future__ import annotations

import math
from typing import Any

from knowledge_loader import load_calibration_rules, load_hexagrams, load_trigrams
from models import HexagramResult, MatchInput, RulePrediction


RULE_VERSION = "score-engine-v3.3.0"


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _safe_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _poisson(k: int, lam: float) -> float:
    return math.exp(-lam) * (lam**k) / math.factorial(k)


def _score_text(score: tuple[int, int]) -> str:
    return f"{score[0]}-{score[1]}"


def _outcome(score: tuple[int, int]) -> str:
    if score[0] > score[1]:
        return "體方勝"
    if score[0] < score[1]:
        return "用方勝"
    return "平局"


def _condition_match(
    result: HexagramResult,
    condition_key: str,
    expected: Any,
    main_tags: list[str],
    mutual_tags: list[str],
    changed_tags: list[str],
) -> bool:
    tag_sources = {
        "main_tags_any": main_tags,
        "main_tags_all": main_tags,
        "mutual_tags_any": mutual_tags,
        "mutual_tags_all": mutual_tags,
        "changed_tags_any": changed_tags,
        "changed_tags_all": changed_tags,
    }
    if condition_key in tag_sources:
        actual_tags = set(tag_sources[condition_key])
        expected_tags = set(expected if isinstance(expected, list) else [expected])
        return bool(actual_tags & expected_tags) if condition_key.endswith("_any") else expected_tags.issubset(actual_tags)

    actual = getattr(result, condition_key, None)
    if isinstance(expected, list):
        return actual in expected
    return actual == expected


def match_calibration_rules(result: HexagramResult) -> list[dict[str, Any]]:
    hexagrams = load_hexagrams()
    main_tags = list(hexagrams.get(result.main_hexagram, {}).get("tags", []))
    mutual_tags = list(hexagrams.get(result.mutual_hexagram, {}).get("tags", []))
    changed_tags = list(hexagrams.get(result.changed_hexagram, {}).get("tags", []))

    matched: list[dict[str, Any]] = []
    for rule in load_calibration_rules():
        conditions = rule.get("conditions", {})
        if conditions and all(
            _condition_match(result, key, expected, main_tags, mutual_tags, changed_tags)
            for key, expected in conditions.items()
        ):
            matched.append(rule)
    return matched


def _apply_relation(
    result: HexagramResult,
    body_xg: float,
    use_xg: float,
    reasons: list[str],
) -> tuple[float, float]:
    """體用只作方向風險修正，不能單獨決定勝負。"""
    relation_effects = {
        "body_controls_use": (0.10, -0.16, "體剋用：體方具制約，但剋制耗力；只作中等修正。"),
        "use_controls_body": (-0.16, 0.10, "用剋體：體方效率受阻，但不等於用方必勝。"),
        "use_generates_body": (0.14, -0.03, "用生體：體方獲助力，但仍需本互變支持完成。"),
        "body_generates_use": (-0.04, 0.10, "體生用：視為能量外洩與反擊風險，不再直接等同用方勝。"),
        "equal": (0.0, 0.0, "體用比和：交由本卦、互卦、變卦、足球先驗與動爻共同判斷。"),
    }
    body_delta, use_delta, note = relation_effects.get(
        result.relation_code,
        (0.0, 0.0, "體用關係不明，維持中性。"),
    )
    reasons.append(note)
    return body_xg + body_delta, use_xg + use_delta


def _apply_phase_aware_transition(
    result: HexagramResult,
    body_xg: float,
    use_xg: float,
    reasons: list[str],
) -> tuple[float, float]:
    """動爻只改變比賽的一個時段，不把變卦當成整場完全替換。"""
    trigrams = load_trigrams()
    phase_weight = {1: 0.24, 2: 0.22, 3: 0.20, 4: 0.18, 5: 0.16, 6: 0.14}.get(result.moving_line, 0.18)

    if result.moving_side == "體方":
        before = trigrams[result.body_gua]
        after = trigrams[result.changed_body_gua]
        attack_shift = float(after["attack_rating"]) - float(before["attack_rating"])
        defense_shift = float(after["defense_rating"]) - float(before["defense_rating"])
        body_xg += phase_weight * attack_shift
        use_xg -= phase_weight * 0.55 * defense_shift
        reasons.append(
            f"動爻在體方：{result.body_transition}只按時段權重{phase_weight:.2f}修正；"
            "原卦前段能力仍保留，避免把『先得勢後收住』誤判成整場無進球。"
        )
    else:
        before = trigrams[result.use_gua]
        after = trigrams[result.changed_use_gua]
        attack_shift = float(after["attack_rating"]) - float(before["attack_rating"])
        defense_shift = float(after["defense_rating"]) - float(before["defense_rating"])
        use_xg += phase_weight * attack_shift
        body_xg -= phase_weight * 0.55 * defense_shift
        reasons.append(
            f"動爻在用方：{result.use_transition}只按時段權重{phase_weight:.2f}修正；"
            "不把後段轉象機械套成整場方向。"
        )
    return body_xg, use_xg


def _apply_football_prior(
    match: MatchInput | None,
    body_xg: float,
    use_xg: float,
    reasons: list[str],
) -> tuple[float, float, dict[str, Any]]:
    if match is None:
        return body_xg, use_xg, {
            "body_strength_rating": 50.0,
            "use_strength_rating": 50.0,
            "prior_confidence": 0.0,
            "venue": "未提供",
            "shift": 0.0,
        }

    body_rating = _clamp(_safe_float(getattr(match, "body_strength_rating", 50.0), 50.0), 0.0, 100.0)
    use_rating = _clamp(_safe_float(getattr(match, "use_strength_rating", 50.0), 50.0), 0.0, 100.0)
    confidence = _clamp(_safe_float(getattr(match, "prior_confidence", 0.5), 0.5), 0.0, 1.0)
    venue = str(getattr(match, "venue", "中立場") or "中立場")

    normalized_gap = _clamp((body_rating - use_rating) / 50.0, -1.0, 1.0)
    shift = 0.72 * normalized_gap * confidence
    body_xg += shift
    use_xg -= shift

    if "體方主場" in venue:
        body_xg += 0.08 * confidence
        use_xg -= 0.03 * confidence
    elif "用方主場" in venue:
        use_xg += 0.08 * confidence
        body_xg -= 0.03 * confidence

    reasons.append(
        f"賽前足球先驗：體{body_rating:.0f}、用{use_rating:.0f}、可信度{confidence:.0%}、{venue}；"
        f"對雙方期望進球作對稱修正{shift:+.2f}。此先驗不參與起卦字數。"
    )
    return body_xg, use_xg, {
        "body_strength_rating": round(body_rating, 2),
        "use_strength_rating": round(use_rating, 2),
        "prior_confidence": round(confidence, 3),
        "venue": venue,
        "shift": round(shift, 4),
    }


def _rule_scale(rule: dict[str, Any]) -> float:
    status = str(rule.get("status", "")).lower()
    if status == "verified":
        return 1.0
    if status == "reviewed":
        return 0.65
    if status == "general":
        return 0.35
    return 0.50


def _select_top_scores(
    grid: list[tuple[tuple[int, int], float]],
    outcome_probabilities: dict[str, float],
    football_prior: dict[str, Any],
) -> list[tuple[int, int]]:
    ranked = [score for score, _ in grid]
    top = ranked[:3]
    if not top:
        return [(0, 0), (1, 0), (0, 1)]

    dominant_probability = max(outcome_probabilities.values() or [0.0])
    top_outcomes = {_outcome(score) for score in top}
    if len(top_outcomes) == 1 and dominant_probability < 0.68:
        alternative = next((score for score in ranked if _outcome(score) not in top_outcomes), None)
        if alternative is not None:
            top[-1] = alternative

    body_rating = _safe_float(football_prior.get("body_strength_rating"), 50.0)
    use_rating = _safe_float(football_prior.get("use_strength_rating"), 50.0)
    prior_confidence = _safe_float(football_prior.get("prior_confidence"), 0.0)
    rating_gap = body_rating - use_rating
    if abs(rating_gap) >= 12 and prior_confidence >= 0.50 and dominant_probability < 0.72:
        desired = "體方勝" if rating_gap > 0 else "用方勝"
        if all(_outcome(score) != desired for score in top):
            candidate = next((score for score in ranked if _outcome(score) == desired), None)
            if candidate is not None:
                top[-1] = candidate

    output: list[tuple[int, int]] = []
    for score in top + ranked:
        if score not in output:
            output.append(score)
        if len(output) == 3:
            break
    return output


def predict_scores(result: HexagramResult, match: MatchInput | None = None) -> RulePrediction:
    trigrams = load_trigrams()
    hexagrams = load_hexagrams()
    body_tri = trigrams[result.body_gua]
    use_tri = trigrams[result.use_gua]
    main = hexagrams[result.main_hexagram]
    mutual = hexagrams[result.mutual_hexagram]
    changed = hexagrams[result.changed_hexagram]

    reasons: list[str] = []
    diagnostics: list[str] = []
    body_xg = 1.02
    use_xg = 1.02

    # 八卦基礎只建立攻守骨架，不直接決定勝負。
    body_xg += 0.38 * (float(body_tri["attack_rating"]) - 1.0)
    body_xg -= 0.28 * (float(use_tri["defense_rating"]) - 1.0)
    use_xg += 0.38 * (float(use_tri["attack_rating"]) - 1.0)
    use_xg -= 0.28 * (float(body_tri["defense_rating"]) - 1.0)
    reasons.append(f"八卦攻守骨架：體{result.body_gua}、用{result.use_gua}；不把卦數直接當進球數。")

    # 本卦主局、互卦中段、變卦後段，主要調整總節奏。
    pace_index = 0.55 * float(main["pace"]) + 0.25 * float(mutual["pace"]) + 0.20 * float(changed["pace"])
    pace_goal_delta = 0.12 * pace_index
    body_xg += pace_goal_delta
    use_xg += pace_goal_delta
    reasons.append(
        f"本互變節奏：{result.main_hexagram}→{result.mutual_hexagram}→{result.changed_hexagram}，"
        f"綜合節奏指數{pace_index:+.2f}，只共同修正總進球。"
    )

    body_xg, use_xg = _apply_relation(result, body_xg, use_xg, reasons)
    body_xg, use_xg = _apply_phase_aware_transition(result, body_xg, use_xg, reasons)
    body_xg, use_xg, football_prior = _apply_football_prior(match, body_xg, use_xg, reasons)

    matched_rules = match_calibration_rules(result)
    score_multipliers: dict[str, float] = {}
    score_penalties: dict[str, float] = {}
    for rule in matched_rules:
        scale = _rule_scale(rule)
        effects = rule.get("effects", {})
        body_xg += scale * float(effects.get("body_delta", 0.0))
        use_xg += scale * float(effects.get("use_delta", 0.0))
        total_delta = scale * float(effects.get("total_delta", 0.0))
        body_xg += total_delta / 2
        use_xg += total_delta / 2
        for score, multiplier in effects.get("boost_scores", {}).items():
            adjusted = 1.0 + (float(multiplier) - 1.0) * scale
            score_multipliers[score] = score_multipliers.get(score, 1.0) * adjusted
        for score, multiplier in effects.get("penalize_scores", {}).items():
            adjusted = 1.0 + (float(multiplier) - 1.0) * scale
            score_penalties[score] = score_penalties.get(score, 1.0) * adjusted
        reasons.append(f"校準規則〔{rule['name']}〕按狀態權重{scale:.0%}套用：{rule['lesson']}")

    body_xg = _clamp(body_xg, 0.15, 4.3)
    use_xg = _clamp(use_xg, 0.15, 4.3)

    grid: list[tuple[tuple[int, int], float]] = []
    for body_goals in range(0, 6):
        for use_goals in range(0, 6):
            score = (body_goals, use_goals)
            text = _score_text(score)
            weight = _poisson(body_goals, body_xg) * _poisson(use_goals, use_xg)
            if text in main.get("score_patterns", []):
                weight *= 1.24
            if text in mutual.get("score_patterns", []):
                weight *= 1.08
            if text in changed.get("score_patterns", []):
                weight *= 1.10
            weight *= score_multipliers.get(text, 1.0)
            weight *= score_penalties.get(text, 1.0)
            if body_goals + use_goals >= 7:
                weight *= 0.45
            grid.append((score, weight))

    grid.sort(key=lambda item: item[1], reverse=True)
    total_weight = sum(weight for _, weight in grid) or 1.0
    outcome_probabilities = {"體方勝": 0.0, "平局": 0.0, "用方勝": 0.0}
    for score, weight in grid:
        outcome_probabilities[_outcome(score)] += weight / total_weight
    outcome_probabilities = {key: round(value, 4) for key, value in outcome_probabilities.items()}

    top_scores = _select_top_scores(grid, outcome_probabilities, football_prior)
    ordered_outcomes = sorted(outcome_probabilities.items(), key=lambda item: item[1], reverse=True)
    best_outcome, best_probability = ordered_outcomes[0]
    second_probability = ordered_outcomes[1][1]
    if best_probability >= 0.44 and best_probability - second_probability >= 0.07:
        direction = best_outcome
    else:
        direction = "平局或一球差拉鋸"

    top_weight = grid[0][1]
    total_top_12 = sum(weight for _, weight in grid[:12]) or 1.0
    outcome_margin = max(0.0, best_probability - second_probability)
    confidence = _clamp(0.20 + 0.55 * outcome_margin + 0.35 * (top_weight / total_top_12), 0.20, 0.72)

    if result.relation_code == "body_generates_use":
        diagnostics.append("體生用只被視為外洩風險，不可單獨推出用方勝。")
    if len({_outcome(score) for score in top_scores}) == 1 and best_probability < 0.68:
        diagnostics.append("前三選方向過度集中，但勝平負機率未形成強優勢；應保留替代方向。")
    prior_gap = football_prior["body_strength_rating"] - football_prior["use_strength_rating"]
    if abs(prior_gap) >= 12 and football_prior["prior_confidence"] >= 0.50:
        prior_direction = "體方勝" if prior_gap > 0 else "用方勝"
        if best_outcome != prior_direction and best_probability < 0.65:
            diagnostics.append("卦象方向與高可信足球先驗衝突；最終排序必須交由AI作證據審查，不可只信單一規則。")
    if not diagnostics:
        diagnostics.append("未發現單一體用關係壟斷方向或前三選異常集中的系統性警訊。")

    score_grid = [
        {
            "score": _score_text(score),
            "weight": round(weight, 8),
            "probability": round(weight / total_weight, 6),
            "outcome": _outcome(score),
            "rank": index + 1,
        }
        for index, (score, weight) in enumerate(grid)
    ]
    reasons.append(
        f"最終期望進球：{result.body_team}{body_xg:.2f}、{result.use_team}{use_xg:.2f}；"
        f"勝平負機率＝體{outcome_probabilities['體方勝']:.1%}／平{outcome_probabilities['平局']:.1%}／用{outcome_probabilities['用方勝']:.1%}。"
    )

    return RulePrediction(
        scores=top_scores,
        expected_body_goals=round(body_xg, 2),
        expected_use_goals=round(use_xg, 2),
        direction=direction,
        confidence=round(confidence, 3),
        reasons=reasons,
        matched_rules=matched_rules,
        score_grid=score_grid,
        outcome_probabilities=outcome_probabilities,
        diagnostics=diagnostics,
        football_prior=football_prior,
        method=RULE_VERSION,
    )
