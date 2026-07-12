from __future__ import annotations

from collections import Counter
from typing import Any, Mapping

from football_prior import clamp, safe_float
from knowledge_loader import load_hexagrams, load_trigrams
from meihua_engine import BAGUA_NUMBER, ELEMENTS, five_element_relation
from models import HexagramResult, HexagramScript, MatchInput


OPEN_TAGS = {
    "破口": 14, "解局": 14, "爆發": 14, "多球": 13, "火力": 12, "缺口": 12,
    "防線鬆動": 14, "強行切開": 13, "連續衝擊": 12, "衝擊": 9, "高壓": 8,
    "滲透": 9, "失誤": 8, "反擊": 7, "交換": 8, "過載": 10, "臨界": 9,
    "失衡": 9, "突發": 8, "門前危機": 8, "暴露": 8, "雙方機會": 10,
    "雙方活躍": 10, "釋放": 9, "裂口": 10, "二波": 7, "最後一步": 6,
}
CLOSE_TAGS = {
    "收束": 14, "零球": 15, "封鎖": 14, "受阻": 12, "低效": 10, "閉塞": 14,
    "雙止": 15, "節制": 12, "減損": 10, "低比分": 10, "蹇難": 12, "界限": 9,
    "低位": 6, "退守": 7, "收縮": 7, "控局": 5, "阻擋": 9, "防守成功": 10,
    "削弱": 8, "剝落": 9, "土重": 7, "等待": 5, "隱藏": 6, "限制": 7,
}
VOLATILITY_TAGS = {
    "突發": 12, "意外": 12, "失誤": 9, "反覆": 9, "變革": 11, "轉折": 10,
    "重置": 10, "高波動": 14, "失序": 12, "冒進": 9, "未完成": 9,
    "開放結尾": 11, "過載": 10, "臨界": 10, "失衡": 11, "危機": 9,
    "不安定": 10, "拉鋸": 6, "碰撞": 7, "爭持": 6, "回轉": 7,
}

TRIGRAM_DYNAMICS = {"乾": 6, "兌": 6, "離": 11, "震": 14, "巽": 8, "坎": 5, "艮": -12, "坤": -6}
TRIGRAM_CHANNEL = {"乾": 0, "兌": 14, "離": 12, "震": 12, "巽": 9, "坎": 7, "艮": -12, "坤": -7}
TRIGRAM_CLOSURE = {"乾": 2, "兌": -6, "離": -8, "震": -10, "巽": -4, "坎": -3, "艮": 15, "坤": 9}
HIGH_ENERGY_TRIGRAMS = {"震", "巽", "乾", "離"}
GOAL_BIAS = {"極低": -24, "低": -15, "中低": -7, "中": 0, "中高": 8, "高": 15, "極高": 24, "變動": 4}
PHASE_DURATION = {1: 1.00, 2: 0.88, 3: 0.75, 4: 0.62, 5: 0.48, 6: 0.35}


def _tag_signal(tags: list[str], lexicon: Mapping[str, int]) -> float:
    total = 0.0
    for tag in tags:
        matches = [weight for token, weight in lexicon.items() if token in str(tag)]
        if matches:
            total += max(matches)
    return total


def _weighted_stage_signal(
    main_tags: list[str],
    mutual_tags: list[str],
    changed_tags: list[str],
    lexicon: Mapping[str, int],
) -> float:
    return (
        0.50 * _tag_signal(main_tags, lexicon)
        + 0.25 * _tag_signal(mutual_tags, lexicon)
        + 0.25 * _tag_signal(changed_tags, lexicon)
    )


def _weighted_trigram_signal(result: HexagramResult, table: Mapping[str, float]) -> float:
    return (
        0.30 * safe_float(table.get(result.body_gua), 0.0)
        + 0.30 * safe_float(table.get(result.use_gua), 0.0)
        + 0.20 * safe_float(table.get(result.changed_body_gua), 0.0)
        + 0.20 * safe_float(table.get(result.changed_use_gua), 0.0)
    )


def _relation_edge(code: str) -> float:
    return {
        "body_controls_use": 1.0,
        "use_generates_body": 0.65,
        "equal": 0.0,
        "body_generates_use": -0.65,
        "use_controls_body": -1.0,
    }.get(str(code or ""), 0.0)


def _changed_relation(result: HexagramResult) -> tuple[str, str, str]:
    if result.changed_relation_code:
        return result.changed_relation_code, result.changed_relation, result.changed_relation_detail
    body_element = result.changed_body_element or ELEMENTS[result.changed_body_gua]
    use_element = result.changed_use_element or ELEMENTS[result.changed_use_gua]
    return five_element_relation(body_element, use_element)


def _phase_label(line: int) -> str:
    return {
        1: "開局早段",
        2: "上半場前中段",
        3: "中段轉折",
        4: "下半場前段",
        5: "下半場後段",
        6: "終場前後段",
    }.get(line, "比賽中段")


def _unique_ints(values: list[int], low: int = 0, high: int = 8) -> list[int]:
    output: list[int] = []
    for value in values:
        bounded = max(low, min(high, int(value)))
        if bounded not in output:
            output.append(bounded)
    return output


def _numeric_signals(result: HexagramResult, mirror_mode: str, openness: float) -> list[dict[str, Any]]:
    body_number = int(result.body_number or BAGUA_NUMBER[result.body_gua])
    use_number = int(result.use_number or BAGUA_NUMBER[result.use_gua])
    changed_body_number = int(result.changed_body_number or BAGUA_NUMBER[result.changed_body_gua])
    changed_use_number = int(result.changed_use_number or BAGUA_NUMBER[result.changed_use_gua])
    signals: list[dict[str, Any]] = []

    original_difference = abs(body_number - use_number)
    if 2 <= original_difference <= 6:
        signals.append(
            {
                "formula": "原始體用卦數差",
                "value": original_difference,
                "strength": 0.45,
                "reason": f"|{body_number}-{use_number}|={original_difference}，只作總球次級錨點。",
            }
        )

    changed_difference = abs(changed_body_number - changed_use_number)
    if 2 <= changed_difference <= 6:
        signals.append(
            {
                "formula": "變卦體用卦數差",
                "value": changed_difference,
                "strength": 0.50,
                "reason": f"|{changed_body_number}-{changed_use_number}|={changed_difference}，只作終局總球次級錨點。",
            }
        )

    moving_before = body_number if result.moving_side == "體方" else use_number
    moving_after = changed_body_number if result.moving_side == "體方" else changed_use_number
    moving_after_gua = result.changed_body_gua if result.moving_side == "體方" else result.changed_use_gua
    resonance_total = moving_before + moving_after
    if (
        mirror_mode == "同數共振"
        and moving_before != moving_after
        and moving_after_gua in HIGH_ENERGY_TRIGRAMS
        and openness >= 60
        and 3 <= resonance_total <= 8
    ):
        signals.append(
            {
                "formula": "同數動方前後疊加",
                "value": resonance_total,
                "strength": 0.90,
                "reason": f"同數結構中動方{moving_before}+{moving_after}={resonance_total}，且轉入{moving_after_gua}高動能卦。",
            }
        )

    counts = Counter(int(signal["value"]) for signal in signals)
    for value, count in counts.items():
        if count >= 2:
            signals.append(
                {
                    "formula": "兩條獨立數路收斂",
                    "value": value,
                    "strength": 0.85,
                    "reason": f"至少兩條預先限定數路同時指向總球{value}。",
                }
            )
    return signals


def _add_candidate(
    candidates: list[dict[str, Any]],
    body_goals: int,
    use_goals: int,
    reason: str,
    archetype: str,
) -> None:
    body_goals = max(0, min(10, int(body_goals)))
    use_goals = max(0, min(10, int(use_goals)))
    score = f"{body_goals}-{use_goals}"
    if any(item["score"] == score for item in candidates):
        return
    rank = len(candidates)
    rank_strengths = [1.00, 0.55, 0.32, 0.20, 0.13, 0.09, 0.06, 0.04]
    candidates.append(
        {
            "score": score,
            "body_goals": body_goals,
            "use_goals": use_goals,
            "total_goals": body_goals + use_goals,
            "archetype": archetype,
            "script_strength": rank_strengths[min(rank, len(rank_strengths) - 1)],
            "reason": reason,
        }
    )


def _allocate_score(
    total: int,
    body_share: float,
    body_ownership: float,
    use_ownership: float,
    body_finishing: float,
    use_finishing: float,
    btts_signal: bool,
    rout_side: str,
    one_sided_side: str,
) -> tuple[int, int]:
    if total <= 0:
        return 0, 0
    if total == 1:
        return (1, 0) if body_ownership >= use_ownership else (0, 1)

    if rout_side:
        losing_finishing = use_finishing if rout_side == "體方" else body_finishing
        concentrated = abs(body_ownership - use_ownership) >= 45 or abs(body_share - 0.50) >= 0.28
        loser_goals = 0 if losing_finishing < 48 or concentrated else 1
        loser_goals = min(loser_goals, max(0, total - 2))
        return (total - loser_goals, loser_goals) if rout_side == "體方" else (loser_goals, total - loser_goals)

    if one_sided_side and not btts_signal:
        return (total, 0) if one_sided_side == "體方" else (0, total)

    body_goals = int(total * body_share + 0.5)
    body_goals = max(0, min(total, body_goals))
    use_goals = total - body_goals
    if btts_signal and total >= 2:
        if body_goals == 0:
            body_goals, use_goals = 1, total - 1
        elif use_goals == 0:
            body_goals, use_goals = total - 1, 1
    return body_goals, use_goals


def interpret_hexagram_script(
    result: HexagramResult,
    match: MatchInput | None,
    football_prior: Mapping[str, Any],
) -> HexagramScript:
    trigrams = load_trigrams()
    hexagrams = load_hexagrams()
    main = hexagrams[result.main_hexagram]
    mutual = hexagrams[result.mutual_hexagram]
    changed = hexagrams[result.changed_hexagram]
    main_tags = list(main.get("tags", []))
    mutual_tags = list(mutual.get("tags", []))
    changed_tags = list(changed.get("tags", []))

    open_signal = _weighted_stage_signal(main_tags, mutual_tags, changed_tags, OPEN_TAGS)
    close_signal = _weighted_stage_signal(main_tags, mutual_tags, changed_tags, CLOSE_TAGS)
    volatility_signal = _weighted_stage_signal(main_tags, mutual_tags, changed_tags, VOLATILITY_TAGS)
    pace_index = (
        0.50 * safe_float(main.get("pace"), 0.0)
        + 0.25 * safe_float(mutual.get("pace"), 0.0)
        + 0.25 * safe_float(changed.get("pace"), 0.0)
    )
    bias_index = (
        0.50 * GOAL_BIAS.get(str(main.get("goal_bias", "中")), 0)
        + 0.25 * GOAL_BIAS.get(str(mutual.get("goal_bias", "中")), 0)
        + 0.25 * GOAL_BIAS.get(str(changed.get("goal_bias", "中")), 0)
    )

    dynamics = 48 + 8 * pace_index + _weighted_trigram_signal(result, TRIGRAM_DYNAMICS)
    dynamics += 0.22 * open_signal + 0.25 * volatility_signal - 0.15 * close_signal + 0.20 * bias_index
    channel = 38 + _weighted_trigram_signal(result, TRIGRAM_CHANNEL)
    channel += 0.62 * open_signal - 0.42 * close_signal + 0.35 * bias_index
    closure = 45 + _weighted_trigram_signal(result, TRIGRAM_CLOSURE)
    closure += 0.72 * close_signal - 0.38 * open_signal - 0.45 * bias_index
    volatility = 34 + 0.82 * volatility_signal + 4.0 * abs(safe_float(main.get("pace"), 0) - safe_float(changed.get("pace"), 0))
    if "變動" in {main.get("goal_bias"), mutual.get("goal_bias"), changed.get("goal_bias")}:
        volatility += 7

    changed_relation_code, changed_relation, _ = _changed_relation(result)
    initial_edge = _relation_edge(result.relation_code)
    changed_edge = _relation_edge(changed_relation_code)
    relation_reversal = initial_edge * changed_edge < 0
    if relation_reversal:
        dynamics += 12
        channel += 20
        closure -= 12
        volatility += 32

    same_gua = result.body_gua == result.use_gua
    mirror_mode = "無"
    if same_gua:
        if channel >= 58 and dynamics >= 58:
            mirror_mode = "同數共振"
            dynamics += 8
            channel += 10
            closure -= 8
            volatility += 8
        else:
            mirror_mode = "鏡像對消"
            dynamics -= 5
            channel -= 8
            closure += 20
    if same_gua and result.main_hexagram == result.mutual_hexagram and mirror_mode == "鏡像對消":
        closure += 8

    dynamics = clamp(dynamics, 0.0, 100.0)
    channel = clamp(channel, 0.0, 100.0)
    closure = clamp(closure, 0.0, 100.0)
    volatility = clamp(volatility, 0.0, 100.0)

    body_tri = trigrams[result.body_gua]
    use_tri = trigrams[result.use_gua]
    changed_body_tri = trigrams[result.changed_body_gua]
    changed_use_tri = trigrams[result.changed_use_gua]
    duration = PHASE_DURATION.get(result.moving_line, 0.60)
    body_attack_shift = safe_float(changed_body_tri.get("attack_rating"), 1.0) - safe_float(body_tri.get("attack_rating"), 1.0)
    use_attack_shift = safe_float(changed_use_tri.get("attack_rating"), 1.0) - safe_float(use_tri.get("attack_rating"), 1.0)

    rating_gap = safe_float(football_prior.get("rating_gap"), 0.0)
    prior_confidence = safe_float(football_prior.get("prior_confidence"), 0.0)
    ownership_edge = 0.35 * rating_gap * prior_confidence
    ownership_edge += 12.0 * initial_edge + 10.0 * changed_edge
    ownership_edge += 12.0 * (
        safe_float(body_tri.get("attack_rating"), 1.0) - safe_float(use_tri.get("attack_rating"), 1.0)
    )
    ownership_edge += 8.0 * duration * (body_attack_shift - use_attack_shift)
    ownership_edge += 6.0 if result.moving_side == "體方" else -6.0
    ownership_edge = clamp(ownership_edge, -45.0, 45.0)
    body_ownership = 50.0 + ownership_edge
    use_ownership = 50.0 - ownership_edge

    body_attack = 0.65 * safe_float(body_tri.get("attack_rating"), 1.0) + 0.35 * safe_float(changed_body_tri.get("attack_rating"), 1.0)
    use_attack = 0.65 * safe_float(use_tri.get("attack_rating"), 1.0) + 0.35 * safe_float(changed_use_tri.get("attack_rating"), 1.0)
    body_defense = 0.65 * safe_float(body_tri.get("defense_rating"), 1.0) + 0.35 * safe_float(changed_body_tri.get("defense_rating"), 1.0)
    use_defense = 0.65 * safe_float(use_tri.get("defense_rating"), 1.0) + 0.35 * safe_float(changed_use_tri.get("defense_rating"), 1.0)
    body_finishing = 48 + 32 * (body_attack - 1.0) - 22 * (use_defense - 1.0)
    use_finishing = 48 + 32 * (use_attack - 1.0) - 22 * (body_defense - 1.0)
    body_finishing += 0.30 * (body_ownership - 50) + 0.18 * (channel - 50) - 0.16 * (closure - 50)
    use_finishing += 0.30 * (use_ownership - 50) + 0.18 * (channel - 50) - 0.16 * (closure - 50)
    if mirror_mode == "鏡像對消":
        body_finishing -= 8
        use_finishing -= 8
    body_finishing = clamp(body_finishing, 0.0, 100.0)
    use_finishing = clamp(use_finishing, 0.0, 100.0)

    openness = 0.32 * dynamics + 0.38 * channel + 0.18 * volatility + 0.12 * (100.0 - closure)
    effective_gap = abs(rating_gap) * prior_confidence
    dominance = abs(body_ownership - use_ownership)
    winner_finishing = body_finishing if body_ownership >= use_ownership else use_finishing
    rout_signal = (
        effective_gap >= 22 and dominance >= 22 and channel >= 48 and winner_finishing >= 55
    ) or (
        effective_gap >= 45 and dominance >= 25 and channel >= 38 and winner_finishing >= 55
    )
    rout_side = "體方" if rout_signal and body_ownership > use_ownership else ("用方" if rout_signal else "")
    zero_goal_gate = (
        (closure >= 60 and channel <= 38 and volatility < 60)
        or (closure >= 70 and channel <= 48 and volatility < 68)
        or (mirror_mode == "鏡像對消" and channel < 55)
    )
    if rout_signal or (effective_gap >= 30 and dominance >= 20):
        zero_goal_gate = False
    elif relation_reversal and volatility >= 68:
        zero_goal_gate = False
    reversal_open = relation_reversal and volatility >= 64 and channel >= 45
    high_score_gate = (
        openness >= 62
        or rout_signal
        or reversal_open
        or (mirror_mode == "同數共振" and channel >= 58)
    )
    explosive = (
        openness >= 74
        or (rout_signal and openness >= 55)
        or (dynamics >= 78 and channel >= 60 and closure <= 35)
    )
    btts_signal = not zero_goal_gate and (
        (min(body_finishing, use_finishing) >= 52 and channel >= 54)
        or (volatility >= 70 and min(body_finishing, use_finishing) >= 44)
    )
    one_sided_side = ""
    finishing_gap = body_finishing - use_finishing
    if not zero_goal_gate and not btts_signal:
        if body_ownership - use_ownership >= 24 and finishing_gap >= 8:
            one_sided_side = "體方"
        elif use_ownership - body_ownership >= 24 and finishing_gap <= -8:
            one_sided_side = "用方"

    if zero_goal_gate:
        environment = "封閉／零球閘門"
    elif explosive:
        environment = "爆發／崩盤風險"
    elif high_score_gate:
        environment = "開放／高比分尾部"
    elif volatility >= 68:
        environment = "拉鋸／反轉"
    else:
        environment = "受控／中等總球"

    if initial_edge > 0.2 and changed_edge < -0.2:
        trajectory = "體方前段得勢，用方後段反轉"
    elif initial_edge < -0.2 and changed_edge > 0.2:
        trajectory = "用方前段得勢，體方後段反轉"
    elif initial_edge > 0.2 and changed_edge >= 0:
        trajectory = "體方優勢延續，動爻決定擴大或守成"
    elif initial_edge < -0.2 and changed_edge <= 0:
        trajectory = "用方優勢延續，動爻決定擴大或守成"
    elif result.moving_side == "體方":
        trajectory = "前段均衡，體方於變動時段取得主動"
    else:
        trajectory = "前段均衡，用方於變動時段取得主動"

    numeric_signals = _numeric_signals(result, mirror_mode, openness)
    base_total = safe_float(football_prior.get("total_lambda"), 2.55)
    expected_total = base_total + 1.25 * (openness - 50.0) / 50.0
    if rout_signal:
        expected_total += 0.70
        expected_total = max(expected_total, 4.20 + max(0.0, effective_gap - 35.0) * 0.025)
    if zero_goal_gate:
        expected_total = min(expected_total, 1.35)
    elif explosive:
        expected_total = max(expected_total, 4.40)
    elif high_score_gate:
        expected_total = max(expected_total, 3.35)
    expected_total = clamp(expected_total, 0.40, 7.00)

    strong_numeric = [int(signal["value"]) for signal in numeric_signals if safe_float(signal.get("strength"), 0.0) >= 0.80]
    mismatch_target = int(clamp(round(3.5 + effective_gap / 20.0), 5, 7)) if rout_signal else 0
    center = int(expected_total + 0.5)
    if zero_goal_gate:
        total_targets = [0, 1, 2]
    elif explosive:
        total_targets = strong_numeric + [max(4, center), max(5, center + 1), mismatch_target or 6, max(3, center - 1)]
    elif high_score_gate:
        total_targets = strong_numeric + [max(3, center), max(4, center + 1), max(2, center - 1), 5]
    elif volatility >= 68:
        total_targets = strong_numeric + [max(2, center), max(3, center + 1), max(1, center - 1), 4]
    else:
        total_targets = strong_numeric + [max(1, center), max(0, center - 1), min(4, center + 1)]
    total_targets = _unique_ints(total_targets)[:4]
    while len(total_targets) < 3:
        total_targets = _unique_ints(total_targets + [len(total_targets) + 1])

    prior_body_share = safe_float(football_prior.get("body_goal_share"), 0.50)
    body_share = clamp(0.55 * prior_body_share + 0.45 * (body_ownership / 100.0), 0.06, 0.94)
    candidates: list[dict[str, Any]] = []
    if zero_goal_gate:
        _add_candidate(candidates, 0, 0, "封閉訊號與破門通道同時不足，先保留零進球劇本。", "零球")

    for total in total_targets:
        body_goals, use_goals = _allocate_score(
            total,
            body_share,
            body_ownership,
            use_ownership,
            body_finishing,
            use_finishing,
            btts_signal,
            rout_side,
            one_sided_side,
        )
        reason = (
            f"總球錨點{total}；能量歸屬體{body_ownership:.0f}/用{use_ownership:.0f}，"
            f"完成通道體{body_finishing:.0f}/用{use_finishing:.0f}。"
        )
        archetype = "大勝" if rout_side else ("雙方進球" if btts_signal else ("單向破門" if one_sided_side else "主劇本"))
        _add_candidate(candidates, body_goals, use_goals, reason, archetype)

    largest_total = max(total_targets)
    if btts_signal and largest_total >= 4:
        if abs(body_ownership - use_ownership) <= 22 or volatility >= 72:
            _add_candidate(
                candidates,
                (largest_total + 1) // 2,
                largest_total // 2,
                "雙方皆有破門通道且波動高，保留對攻或追平分配。",
                "對攻拉鋸",
            )
            if largest_total % 2 == 0:
                _add_candidate(
                    candidates,
                    largest_total // 2,
                    largest_total // 2,
                    "能量歸屬接近且終局未完全收束，保留高比分平局。",
                    "高比分平局",
                )

    if rout_side:
        rout_total = max(4, largest_total)
        _add_candidate(
            candidates,
            rout_total if rout_side == "體方" else 0,
            0 if rout_side == "體方" else rout_total,
            "足球先驗差、能量歸屬與防線破口同向，保留集中零封大勝。",
            "零封大勝",
        )
        loser_goal = 1
        _add_candidate(
            candidates,
            rout_total - loser_goal if rout_side == "體方" else loser_goal,
            loser_goal if rout_side == "體方" else rout_total - loser_goal,
            "強弱差支持大勝，但弱方仍有一次反擊或失誤轉換成果。",
            "大勝帶失球",
        )

    if mirror_mode == "鏡像對消":
        _add_candidate(candidates, 0, 0, "同卦同數且缺少可辨識破口，強度可能互相抵消。", "鏡像僵局")
        _add_candidate(candidates, 1, 1, "鏡像結構若各自只完成一次，比分仍維持平衡。", "鏡像各一球")
    elif mirror_mode == "同數共振" and largest_total >= 4:
        _add_candidate(
            candidates,
            (largest_total + 1) // 2,
            largest_total // 2,
            "同數結構因破門通道充足而共振，不按鏡像僵局處理。",
            "同數共振",
        )

    if relation_reversal:
        reversal_total = max(3, min(5, max(total_targets)))
        changed_winner_body = changed_edge > 0
        winner_goals = reversal_total // 2 + 1
        loser_goals = max(0, reversal_total - winner_goals)
        _add_candidate(
            candidates,
            winner_goals if changed_winner_body else loser_goals,
            loser_goals if changed_winner_body else winner_goals,
            f"生剋由{result.relation_code}轉為{changed_relation_code}，保留後段反轉的一球差劇本。",
            "後段反轉",
        )
        _add_candidate(
            candidates,
            loser_goals if changed_winner_body else winner_goals,
            winner_goals if changed_winner_body else loser_goals,
            "後段追擊已形成破口，但動爻時間窗口有限，亦保留追近而未完全翻盤的分支。",
            "追擊未竟",
        )

    candidates = candidates[:8]
    clarity = max(abs(openness - 50.0), abs(closure - 50.0), 1.15 * abs(body_ownership - 50.0))
    script_weight = 0.18 + 0.0032 * clarity
    if high_score_gate or zero_goal_gate:
        script_weight += 0.04
    if mirror_mode != "無" or relation_reversal:
        script_weight += 0.03
    script_weight = clamp(script_weight, 0.18, 0.46)

    opening_reading = f"本卦{result.main_hexagram}：{main.get('opening', main.get('football', ''))}；初始{result.relation}。"
    middle_reading = f"互卦{result.mutual_hexagram}：{mutual.get('middle', mutual.get('football', ''))}。"
    ending_reading = (
        f"{_phase_label(result.moving_line)}由{result.moving_side}發生{result.body_transition if result.moving_side == '體方' else result.use_transition}，"
        f"變卦{result.changed_hexagram}：{changed.get('ending', changed.get('football', ''))}；終局{changed_relation}。"
    )
    energy_flow_summary = (
        f"{trajectory}。比賽動能{dynamics:.0f}、破門通道{channel:.0f}、收束{closure:.0f}、波動{volatility:.0f}；"
        f"能量歸屬體{body_ownership:.0f}/用{use_ownership:.0f}。"
    )
    reasons = [
        f"先判環境為「{environment}」，再進行卦數與比分分配；卦數不直接當進球。",
        f"鏡像判定：{mirror_mode}；同卦同數只有在破門通道與動能同時充足時才視為共振。",
        f"動爻第{result.moving_line}爻位於{result.moving_side}，時間窗口為{_phase_label(result.moving_line)}，變化幅度受剩餘時間限制。",
        f"高比分閘門={'開' if high_score_gate else '關'}；零球閘門={'開' if zero_goal_gate else '關'}；BTTS訊號={'是' if btts_signal else '否'}。",
    ]
    if relation_reversal:
        reasons.append("本卦與變卦的生剋方向相反，必須保留領先被追、追平或後段反勝劇本。")
    if rout_side:
        reasons.append(f"強弱差、能量歸屬與破門通道同向，{rout_side}具防線崩解與大勝尾部。")
    elif one_sided_side:
        reasons.append(f"雙方完成通道不對稱且能量集中，{one_sided_side}具單向破門、對手零球的主要分支。")
    reasons.extend(str(signal["reason"]) for signal in numeric_signals)

    return HexagramScript(
        environment=environment,
        trajectory=trajectory,
        opening_reading=opening_reading,
        middle_reading=middle_reading,
        ending_reading=ending_reading,
        energy_flow_summary=energy_flow_summary,
        dynamics_score=round(dynamics, 2),
        scoring_channel_score=round(channel, 2),
        closure_score=round(closure, 2),
        volatility_score=round(volatility, 2),
        body_ownership=round(body_ownership, 2),
        use_ownership=round(use_ownership, 2),
        body_finishing=round(body_finishing, 2),
        use_finishing=round(use_finishing, 2),
        mirror_mode=mirror_mode,
        high_score_gate=bool(high_score_gate),
        zero_goal_gate=bool(zero_goal_gate),
        btts_signal=bool(btts_signal),
        rout_side=rout_side,
        one_sided_side=one_sided_side,
        total_goal_targets=total_targets,
        numeric_signals=numeric_signals,
        candidate_scores=candidates,
        reasons=reasons,
        script_weight=round(script_weight, 4),
    )


__all__ = ["interpret_hexagram_script"]
