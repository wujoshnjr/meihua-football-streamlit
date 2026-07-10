from __future__ import annotations

import math
from typing import Any

from knowledge_loader import load_calibration_rules, load_hexagrams, load_trigrams
from models import HexagramResult, RulePrediction


RULE_VERSION = "score-engine-v3.1.0"


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _poisson(k: int, lam: float) -> float:
    return math.exp(-lam) * (lam**k) / math.factorial(k)


def _score_text(score: tuple[int, int]) -> str:
    return f"{score[0]}-{score[1]}"


def _condition_match(result: HexagramResult, condition_key: str, expected: Any, main_tags: list[str], mutual_tags: list[str], changed_tags: list[str]) -> bool:
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
        if all(
            _condition_match(result, key, expected, main_tags, mutual_tags, changed_tags)
            for key, expected in conditions.items()
        ):
            matched.append(rule)
    return matched


def _apply_relation(result: HexagramResult, body_xg: float, use_xg: float, reasons: list[str]) -> tuple[float, float]:
    relation_effects = {
        "body_controls_use": (0.18, -0.28, "體剋用：體方制約用方，但保留剋制耗力。"),
        "use_controls_body": (-0.32, 0.22, "用剋體：體方完成度下修，用方破局能力上修。"),
        "use_generates_body": (0.28, -0.08, "用生體：體方獲得助力，進球期望上修。"),
        "body_generates_use": (-0.12, 0.28, "體生用：體方外洩，用方反擊與至少一球風險上修。"),
        "equal": (0.0, 0.0, "體用比和：不先偏任何一方，交由本互變決定。"),
    }
    body_delta, use_delta, note = relation_effects.get(result.relation_code, (0.0, 0.0, "體用關係不明，維持中性。"))
    reasons.append(note)
    return body_xg + body_delta, use_xg + use_delta


def _apply_transition(result: HexagramResult, body_xg: float, use_xg: float, reasons: list[str]) -> tuple[float, float]:
    trigrams = load_trigrams()
    if result.moving_side == "體方":
        before = trigrams[result.body_gua]
        after = trigrams[result.changed_body_gua]
        attack_shift = float(after["attack_rating"]) - float(before["attack_rating"])
        defense_shift = float(after["defense_rating"]) - float(before["defense_rating"])
        body_xg += 0.45 * attack_shift
        use_xg -= 0.22 * defense_shift
        reasons.append(f"動爻在體方：{result.body_transition}，按攻守屬性修正體方後段。")
    else:
        before = trigrams[result.use_gua]
        after = trigrams[result.changed_use_gua]
        attack_shift = float(after["attack_rating"]) - float(before["attack_rating"])
        defense_shift = float(after["defense_rating"]) - float(before["defense_rating"])
        use_xg += 0.45 * attack_shift
        body_xg -= 0.22 * defense_shift
        reasons.append(f"動爻在用方：{result.use_transition}，按攻守屬性修正用方後段。")
    return body_xg, use_xg


def predict_scores(result: HexagramResult) -> RulePrediction:
    trigrams = load_trigrams()
    hexagrams = load_hexagrams()
    body_tri = trigrams[result.body_gua]
    use_tri = trigrams[result.use_gua]
    main = hexagrams[result.main_hexagram]
    mutual = hexagrams[result.mutual_hexagram]
    changed = hexagrams[result.changed_hexagram]

    reasons: list[str] = []
    body_xg = 1.05
    use_xg = 1.05

    # 八卦自身進攻能力與對手防守能力。
    body_xg += 0.42 * (float(body_tri["attack_rating"]) - 1.0)
    body_xg -= 0.34 * (float(use_tri["defense_rating"]) - 1.0)
    use_xg += 0.42 * (float(use_tri["attack_rating"]) - 1.0)
    use_xg -= 0.34 * (float(body_tri["defense_rating"]) - 1.0)
    reasons.append(f"八卦基礎：體{result.body_gua}與用{result.use_gua}的攻守屬性建立原始進球骨架。")

    # 本卦主局、互卦中段、變卦後段。
    pace_index = 0.55 * float(main["pace"]) + 0.25 * float(mutual["pace"]) + 0.20 * float(changed["pace"])
    pace_goal_delta = 0.16 * pace_index
    body_xg += pace_goal_delta
    use_xg += pace_goal_delta
    reasons.append(
        f"本互變節奏：{result.main_hexagram}→{result.mutual_hexagram}→{result.changed_hexagram}，"
        f"綜合節奏指數 {pace_index:+.2f}。"
    )

    body_xg, use_xg = _apply_relation(result, body_xg, use_xg, reasons)
    body_xg, use_xg = _apply_transition(result, body_xg, use_xg, reasons)

    matched_rules = match_calibration_rules(result)
    score_multipliers: dict[str, float] = {}
    score_penalties: dict[str, float] = {}
    for rule in matched_rules:
        effects = rule.get("effects", {})
        body_xg += float(effects.get("body_delta", 0.0))
        use_xg += float(effects.get("use_delta", 0.0))
        total_delta = float(effects.get("total_delta", 0.0))
        body_xg += total_delta / 2
        use_xg += total_delta / 2
        for score, multiplier in effects.get("boost_scores", {}).items():
            score_multipliers[score] = score_multipliers.get(score, 1.0) * float(multiplier)
        for score, multiplier in effects.get("penalize_scores", {}).items():
            score_penalties[score] = score_penalties.get(score, 1.0) * float(multiplier)
        reasons.append(f"校準規則〔{rule['name']}〕：{rule['lesson']}")

    body_xg = _clamp(body_xg, 0.15, 4.3)
    use_xg = _clamp(use_xg, 0.15, 4.3)

    grid: list[tuple[tuple[int, int], float]] = []
    for body_goals in range(0, 6):
        for use_goals in range(0, 6):
            score = (body_goals, use_goals)
            text = _score_text(score)
            weight = _poisson(body_goals, body_xg) * _poisson(use_goals, use_xg)

            # 六十四卦知識庫的典型劇本只作柔性加權，不作硬套。
            if text in main.get("score_patterns", []):
                weight *= 1.28
            if text in mutual.get("score_patterns", []):
                weight *= 1.10
            if text in changed.get("score_patterns", []):
                weight *= 1.12
            weight *= score_multipliers.get(text, 1.0)
            weight *= score_penalties.get(text, 1.0)

            # 避免極端比分僅因高卦數被硬推上去。
            if body_goals + use_goals >= 7:
                weight *= 0.45
            grid.append((score, weight))

    grid.sort(key=lambda item: item[1], reverse=True)
    top_scores: list[tuple[int, int]] = []
    for score, _ in grid:
        if score not in top_scores:
            top_scores.append(score)
        if len(top_scores) == 3:
            break

    top_weight = grid[0][1]
    total_top_12 = sum(weight for _, weight in grid[:12]) or 1.0
    confidence = _clamp(top_weight / total_top_12 + 0.18, 0.20, 0.68)

    if body_xg - use_xg >= 0.28:
        direction = "體方勝"
    elif use_xg - body_xg >= 0.28:
        direction = "用方勝"
    else:
        direction = "平局或一球差拉鋸"

    score_grid = [
        {"score": _score_text(score), "weight": round(weight, 6)}
        for score, weight in grid[:15]
    ]
    reasons.append(
        f"最終期望進球：{result.body_team} {body_xg:.2f}，{result.use_team} {use_xg:.2f}；"
        "比分以0至5球網格排序，而非把卦數直接當進球數。"
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
        method=RULE_VERSION,
    )
