from __future__ import annotations

from typing import Any, Mapping

from football_prior import build_football_prior, clamp, outcome_probabilities, poisson_grid, safe_float
from hexagram_script import interpret_hexagram_script
from knowledge_loader import load_calibration_rules, load_hexagrams, load_trigrams
from models import HexagramResult, HexagramScript, MatchInput, RulePrediction
from version import RULE_VERSION


HEXAGRAM_ADJUSTMENT_CAP = 0.25


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
            matched.append(dict(rule))
    return matched


def _rule_scale(rule: Mapping[str, Any]) -> float:
    """Only promoted rules may materially affect a future prediction.

    A rule created from one post-match example remains a hypothesis and receives
    zero predictive weight. This prevents a known score from being encoded back
    into the next prediction before it survives a holdout review.
    """
    status = str(rule.get("status", "hypothesis")).strip().lower()
    if status == "verified":
        evidence_count = int(safe_float(rule.get("evidence_count"), 0.0))
        holdout_count = int(safe_float(rule.get("holdout_count"), 0.0))
        validation_status = str(rule.get("validation_status", "")).strip().lower()
        return 1.0 if evidence_count >= 3 and holdout_count >= 10 and validation_status == "passed" else 0.0
    if status == "reviewed":
        return 0.35 if int(safe_float(rule.get("evidence_count"), 0.0)) >= 3 else 0.0
    if status == "general":
        return 0.20
    return 0.0


def _apply_relation(
    result: HexagramResult,
    body_delta: float,
    use_delta: float,
    reasons: list[str],
) -> tuple[float, float]:
    effects = {
        "body_controls_use": (0.08, -0.10, "體剋用只作制約風險修正，不直接等同體方勝。"),
        "use_controls_body": (-0.10, 0.08, "用剋體只作受阻風險修正，不直接等同用方勝。"),
        "use_generates_body": (0.10, -0.02, "用生體提高體方轉化條件，但用方自身仍可得分。"),
        "body_generates_use": (-0.03, 0.07, "體生用視為外洩與反擊風險，不直接改判用方勝。"),
        "equal": (0.0, 0.0, "體用比和不決勝，交由整條卦線與足球先驗整合。"),
    }
    body_shift, use_shift, note = effects.get(result.relation_code, (0.0, 0.0, "體用關係不明，維持中性。"))
    reasons.append(note)
    return body_delta + body_shift, use_delta + use_shift


def _apply_phase_transition(
    result: HexagramResult,
    body_delta: float,
    use_delta: float,
    reasons: list[str],
) -> tuple[float, float]:
    trigrams = load_trigrams()
    phase_weight = {1: 0.24, 2: 0.22, 3: 0.20, 4: 0.18, 5: 0.16, 6: 0.14}.get(result.moving_line, 0.18)
    if result.moving_side == "體方":
        before, after = trigrams[result.body_gua], trigrams[result.changed_body_gua]
        attack_shift = safe_float(after.get("attack_rating"), 1.0) - safe_float(before.get("attack_rating"), 1.0)
        defense_shift = safe_float(after.get("defense_rating"), 1.0) - safe_float(before.get("defense_rating"), 1.0)
        body_delta += 0.60 * phase_weight * attack_shift
        use_delta -= 0.32 * phase_weight * defense_shift
        reasons.append(f"動爻在體方：{result.body_transition}按時段權重{phase_weight:.2f}修正，原卦前段能力仍保留。")
    else:
        before, after = trigrams[result.use_gua], trigrams[result.changed_use_gua]
        attack_shift = safe_float(after.get("attack_rating"), 1.0) - safe_float(before.get("attack_rating"), 1.0)
        defense_shift = safe_float(after.get("defense_rating"), 1.0) - safe_float(before.get("defense_rating"), 1.0)
        use_delta += 0.60 * phase_weight * attack_shift
        body_delta -= 0.32 * phase_weight * defense_shift
        reasons.append(f"動爻在用方：{result.use_transition}按時段權重{phase_weight:.2f}修正，不把後段轉象替代整場。")
    return body_delta, use_delta


def _bounded_multiplier(base_lambda: float, delta: float) -> tuple[float, float]:
    raw = 1.0 + delta / max(0.35, base_lambda)
    bounded = clamp(raw, 1.0 - HEXAGRAM_ADJUSTMENT_CAP, 1.0 + HEXAGRAM_ADJUSTMENT_CAP)
    return raw, bounded


def _apply_score_patterns(
    grid: list[dict[str, Any]],
    main_patterns: set[str],
    mutual_patterns: set[str],
    changed_patterns: set[str],
    rule_boosts: Mapping[str, float],
    rule_penalties: Mapping[str, float],
) -> list[dict[str, Any]]:
    adjusted: list[dict[str, Any]] = []
    for source in grid:
        row = dict(source)
        score = str(row.get("score", ""))
        modifier = 1.0
        if score in main_patterns:
            modifier *= 1.08
        if score in mutual_patterns:
            modifier *= 1.03
        if score in changed_patterns:
            modifier *= 1.04
        modifier *= safe_float(rule_boosts.get(score), 1.0)
        modifier *= safe_float(rule_penalties.get(score), 1.0)
        modifier = clamp(modifier, 0.75, 1.25)
        row["pattern_multiplier"] = round(modifier, 6)
        row["probability"] = safe_float(row.get("probability"), 0.0) * modifier
        adjusted.append(row)

    total = sum(safe_float(row.get("probability"), 0.0) for row in adjusted) or 1.0
    for row in adjusted:
        row["probability"] = safe_float(row.get("probability"), 0.0) / total
        row["weight"] = row["probability"]
    adjusted.sort(key=lambda row: safe_float(row.get("probability"), 0.0), reverse=True)
    for index, row in enumerate(adjusted, 1):
        row["rank"] = index
    return adjusted


def _apply_script_mixture(
    grid: list[dict[str, Any]],
    script: HexagramScript,
) -> list[dict[str, Any]]:
    """Blend the continuous hexagram script into the bounded Poisson grid.

    The script never invents an unbounded probability surface. It contributes a
    transparent, capped scenario distribution over precomputed score archetypes;
    the football-first Poisson grid retains the remaining mass.
    """
    candidate_weights: dict[str, float] = {}
    candidate_reasons: dict[str, str] = {}
    for candidate in script.candidate_scores:
        score = str(candidate.get("score", "")).strip()
        if not score:
            continue
        candidate_weights[score] = max(
            candidate_weights.get(score, 0.0),
            safe_float(candidate.get("script_strength"), 0.0),
        )
        candidate_reasons[score] = str(candidate.get("reason", "")).strip()

    total_candidate_weight = sum(candidate_weights.values())
    if total_candidate_weight <= 0.0:
        return grid

    script_weight = clamp(safe_float(script.script_weight, 0.0), 0.0, 0.46)
    adjusted: list[dict[str, Any]] = []
    for source in grid:
        row = dict(source)
        score = str(row.get("score", ""))
        scenario_probability = candidate_weights.get(score, 0.0) / total_candidate_weight
        base_probability = safe_float(row.get("probability"), 0.0)
        row["base_probability"] = base_probability
        row["script_probability"] = scenario_probability
        row["script_support"] = bool(scenario_probability > 0.0)
        row["script_strength"] = round(candidate_weights.get(score, 0.0), 6)
        row["script_reason"] = candidate_reasons.get(score, "")
        row["probability"] = (1.0 - script_weight) * base_probability + script_weight * scenario_probability
        row["weight"] = row["probability"]
        adjusted.append(row)

    total = sum(safe_float(row.get("probability"), 0.0) for row in adjusted) or 1.0
    for row in adjusted:
        row["probability"] = safe_float(row.get("probability"), 0.0) / total
        row["weight"] = row["probability"]
    adjusted.sort(key=lambda row: safe_float(row.get("probability"), 0.0), reverse=True)
    for index, row in enumerate(adjusted, 1):
        row["rank"] = index
    return adjusted


def _parse_grid_score(row: Mapping[str, Any]) -> tuple[int, int] | None:
    try:
        return int(row["body_goals"]), int(row["use_goals"])
    except (KeyError, TypeError, ValueError):
        return None


def _select_top_scores(
    grid: list[Mapping[str, Any]],
    probabilities: Mapping[str, float],
    football_prior: Mapping[str, Any],
) -> list[tuple[int, int]]:
    ranked = [score for row in grid if (score := _parse_grid_score(row)) is not None]
    top = ranked[:3]
    if not top:
        return [(0, 0), (1, 0), (0, 1)]

    dominant_probability = max((safe_float(value, 0.0) for value in probabilities.values()), default=0.0)
    top_outcomes = {_outcome(score) for score in top}
    if len(top_outcomes) == 1 and dominant_probability < 0.68:
        alternative = next((score for score in ranked if _outcome(score) not in top_outcomes), None)
        if alternative is not None:
            top[-1] = alternative

    rating_gap = safe_float(football_prior.get("rating_gap"), 0.0)
    confidence = safe_float(football_prior.get("prior_confidence"), 0.0)
    if abs(rating_gap) >= 12 and confidence >= 0.50 and dominant_probability < 0.72:
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
    body_tri, use_tri = trigrams[result.body_gua], trigrams[result.use_gua]
    main, mutual, changed = (
        hexagrams[result.main_hexagram],
        hexagrams[result.mutual_hexagram],
        hexagrams[result.changed_hexagram],
    )

    reasons: list[str] = []
    diagnostics: list[str] = []
    football_prior = build_football_prior(match)
    football_body_lambda = safe_float(football_prior["body_lambda"], 1.275)
    football_use_lambda = safe_float(football_prior["use_lambda"], 1.275)
    reasons.append(
        f"足球基線先建立λ：體{football_body_lambda:.2f}、用{football_use_lambda:.2f}；"
        "只使用0–100實力、先驗可信度與場地，不使用任何卦象或本場賽後資訊。"
    )

    body_delta = 0.0
    use_delta = 0.0
    body_delta += 0.24 * (safe_float(body_tri.get("attack_rating"), 1.0) - 1.0)
    body_delta -= 0.16 * (safe_float(use_tri.get("defense_rating"), 1.0) - 1.0)
    use_delta += 0.24 * (safe_float(use_tri.get("attack_rating"), 1.0) - 1.0)
    use_delta -= 0.16 * (safe_float(body_tri.get("defense_rating"), 1.0) - 1.0)
    reasons.append(f"八卦攻守只修正足球λ：體{result.body_gua}、用{result.use_gua}；卦數不直接等同進球數。")

    pace_index = 0.55 * safe_float(main.get("pace"), 0.0) + 0.25 * safe_float(mutual.get("pace"), 0.0) + 0.20 * safe_float(changed.get("pace"), 0.0)
    pace_delta = 0.08 * pace_index
    body_delta += pace_delta
    use_delta += pace_delta
    reasons.append(
        f"連續卦線：{result.main_hexagram}→{result.mutual_hexagram}→{result.changed_hexagram}，"
        f"節奏指數{pace_index:+.2f}，共同修正總進球環境。"
    )

    body_delta, use_delta = _apply_relation(result, body_delta, use_delta, reasons)
    body_delta, use_delta = _apply_phase_transition(result, body_delta, use_delta, reasons)

    matched_rules = match_calibration_rules(result)
    audited_rules: list[dict[str, Any]] = []
    score_boosts: dict[str, float] = {}
    score_penalties: dict[str, float] = {}
    for rule in matched_rules:
        scale = _rule_scale(rule)
        audited = dict(rule)
        audited["applied_scale"] = scale
        audited["applied"] = scale > 0.0
        audited_rules.append(audited)
        if scale <= 0.0:
            reasons.append(f"命中未達升級門檻的規則〔{rule.get('name', '')}〕，本場權重為0。")
            continue
        effects = rule.get("effects", {})
        body_delta += scale * safe_float(effects.get("body_delta"), 0.0)
        use_delta += scale * safe_float(effects.get("use_delta"), 0.0)
        total_delta = scale * safe_float(effects.get("total_delta"), 0.0)
        body_delta += total_delta / 2.0
        use_delta += total_delta / 2.0
        for score, multiplier in effects.get("boost_scores", {}).items():
            adjusted = 1.0 + (safe_float(multiplier, 1.0) - 1.0) * scale * 0.25
            score_boosts[str(score)] = score_boosts.get(str(score), 1.0) * adjusted
        for score, multiplier in effects.get("penalize_scores", {}).items():
            adjusted = 1.0 + (safe_float(multiplier, 1.0) - 1.0) * scale * 0.25
            score_penalties[str(score)] = score_penalties.get(str(score), 1.0) * adjusted
        reasons.append(f"校準規則〔{rule.get('name', '')}〕按晉級狀態權重{scale:.0%}有限套用。")

    raw_body_multiplier, body_multiplier = _bounded_multiplier(football_body_lambda, body_delta)
    raw_use_multiplier, use_multiplier = _bounded_multiplier(football_use_lambda, use_delta)
    body_lambda = clamp(football_body_lambda * body_multiplier, 0.10, 6.00)
    use_lambda = clamp(football_use_lambda * use_multiplier, 0.10, 6.00)
    reasons.append(
        f"卦象有界修正：體{body_multiplier:.3f}倍、用{use_multiplier:.3f}倍，"
        f"單方上限±{HEXAGRAM_ADJUSTMENT_CAP:.0%}；修正後λ為{body_lambda:.2f}／{use_lambda:.2f}。"
    )
    if abs(raw_body_multiplier - body_multiplier) > 1e-9 or abs(raw_use_multiplier - use_multiplier) > 1e-9:
        diagnostics.append("至少一方的原始卦象修正超出上限，已截斷至±25%，避免卦象壓過足球基線。")
    else:
        diagnostics.append("兩方卦象修正均在±25%研究上限內。")

    raw_grid, tail_mass = poisson_grid(body_lambda, use_lambda)
    pattern_grid = _apply_score_patterns(
        raw_grid,
        set(main.get("score_patterns", [])),
        set(mutual.get("score_patterns", [])),
        set(changed.get("score_patterns", [])),
        score_boosts,
        score_penalties,
    )
    script = interpret_hexagram_script(result, match, football_prior)
    grid = _apply_script_mixture(pattern_grid, script)
    probabilities = outcome_probabilities(grid)
    top_scores = _select_top_scores(grid, probabilities, football_prior)

    ordered_outcomes = sorted(probabilities.items(), key=lambda item: item[1], reverse=True)
    best_outcome, best_probability = ordered_outcomes[0]
    second_probability = ordered_outcomes[1][1]
    direction = best_outcome if best_probability >= 0.44 and best_probability - second_probability >= 0.07 else "平局或一球差拉鋸"
    outcome_margin = max(0.0, best_probability - second_probability)
    top_probability = safe_float(grid[0].get("probability"), 0.0) if grid else 0.0
    confidence = clamp(0.22 + 0.62 * outcome_margin + 0.45 * top_probability, 0.20, 0.74)

    high_total_probability = sum(
        safe_float(row.get("probability"), 0.0)
        for row in grid
        if safe_float(row.get("body_goals"), 0.0) + safe_float(row.get("use_goals"), 0.0) >= 5
    )
    scenario_expected_body_goals = sum(
        safe_float(row.get("probability"), 0.0) * safe_float(row.get("body_goals"), 0.0)
        for row in grid
    )
    scenario_expected_use_goals = sum(
        safe_float(row.get("probability"), 0.0) * safe_float(row.get("use_goals"), 0.0)
        for row in grid
    )
    diagnostics.append(f"五球以上機率尾部保留為{high_total_probability:.1%}，比分網格擴至單方0–10球。")
    diagnostics.append(
        f"連續卦象劇本以{script.script_weight:.0%}情境權重重排比分；"
        f"環境為「{script.environment}」，劇本期望進球{scenario_expected_body_goals:.2f}／{scenario_expected_use_goals:.2f}。"
    )
    if any(not rule.get("applied") for rule in audited_rules):
        diagnostics.append("命中的單場賽後規則仍屬假說，不參與本場排序；需通過留出樣本後才能升級。")
    if len({_outcome(score) for score in top_scores}) == 1 and best_probability < 0.68:
        diagnostics.append("前三選方向過度集中且機率優勢不足，已保留替代方向。")

    compact_grid = [
        {
            "score": str(row.get("score", "")),
            "weight": round(safe_float(row.get("probability"), 0.0), 8),
            "probability": round(safe_float(row.get("probability"), 0.0), 8),
            "outcome": str(row.get("outcome", "")),
            "rank": int(row.get("rank", 0)),
            "body_goals": int(row.get("body_goals", 0)),
            "use_goals": int(row.get("use_goals", 0)),
            "pattern_multiplier": round(safe_float(row.get("pattern_multiplier"), 1.0), 6),
            "base_probability": round(safe_float(row.get("base_probability"), 0.0), 8),
            "script_probability": round(safe_float(row.get("script_probability"), 0.0), 8),
            "script_support": bool(row.get("script_support", False)),
            "script_strength": round(safe_float(row.get("script_strength"), 0.0), 6),
            "script_reason": str(row.get("script_reason", "")),
        }
        for row in grid
    ]
    football_scores = [tuple(int(value) for value in score) for score in football_prior.get("scores", []) if len(score) == 2]
    football_probabilities = dict(football_prior.get("outcome_probabilities", {}))

    reasons.append(
        f"最終機率：體勝{probabilities['體方勝']:.1%}／平{probabilities['平局']:.1%}／用勝{probabilities['用方勝']:.1%}；"
        f"網格外尾端質量{tail_mass:.4%}。"
    )
    reasons.append(script.energy_flow_summary)
    reasons.extend(script.reasons)
    enriched_prior = dict(football_prior)
    enriched_prior.update(
        {
            "hexagram_body_raw_multiplier": round(raw_body_multiplier, 6),
            "hexagram_use_raw_multiplier": round(raw_use_multiplier, 6),
            "hexagram_body_multiplier": round(body_multiplier, 6),
            "hexagram_use_multiplier": round(use_multiplier, 6),
            "hexagram_adjustment_cap": HEXAGRAM_ADJUSTMENT_CAP,
            "adjusted_body_lambda": round(body_lambda, 4),
            "adjusted_use_lambda": round(use_lambda, 4),
            "five_plus_probability": round(high_total_probability, 6),
            "script_environment": script.environment,
            "script_weight": script.script_weight,
            "scenario_expected_body_goals": round(scenario_expected_body_goals, 4),
            "scenario_expected_use_goals": round(scenario_expected_use_goals, 4),
        }
    )

    return RulePrediction(
        scores=top_scores,
        expected_body_goals=round(body_lambda, 3),
        expected_use_goals=round(use_lambda, 3),
        direction=direction,
        confidence=round(confidence, 3),
        reasons=reasons,
        matched_rules=audited_rules,
        score_grid=compact_grid,
        outcome_probabilities={key: round(value, 6) for key, value in probabilities.items()},
        diagnostics=diagnostics,
        football_prior=enriched_prior,
        football_only_scores=football_scores,
        football_only_outcome_probabilities={key: round(safe_float(value, 0.0), 6) for key, value in football_probabilities.items()},
        football_expected_body_goals=round(football_body_lambda, 3),
        football_expected_use_goals=round(football_use_lambda, 3),
        hexagram_body_multiplier=round(body_multiplier, 6),
        hexagram_use_multiplier=round(use_multiplier, 6),
        hexagram_adjustment_cap=HEXAGRAM_ADJUSTMENT_CAP,
        hexagram_script=script.to_dict(),
        scenario_weight=script.script_weight,
        scenario_expected_body_goals=round(scenario_expected_body_goals, 3),
        scenario_expected_use_goals=round(scenario_expected_use_goals, 3),
        method=RULE_VERSION,
    )


__all__ = ["HEXAGRAM_ADJUSTMENT_CAP", "RULE_VERSION", "match_calibration_rules", "predict_scores"]
