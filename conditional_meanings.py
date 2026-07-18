from __future__ import annotations

from typing import Any

from knowledge_loader import load_conditional_trigram_meanings
from models import HexagramResult
from najia_structure import branch_relation


STRENGTH_RANK = {"死": 1, "囚": 2, "休": 3, "相": 4, "旺": 5}
HIGH_ENERGY_TRIGRAMS = {"震", "巽", "離"}
BREAKTHROUGH_HEXAGRAM_MARKERS = ("夬", "噬嗑", "解", "豐", "渙", "革")


def _relation_score(code: str, side: str) -> int:
    body_scores = {
        "body_controls_use": 2,
        "use_generates_body": 1,
        "equal": 0,
        "body_generates_use": -1,
        "use_controls_body": -2,
    }
    score = body_scores[code]
    return score if side == "body" else -score


def _relation_signal(code: str, side: str, signal: str) -> bool:
    if side == "body":
        expected = {
            "supported": "use_generates_body",
            "controls": "body_controls_use",
            "controlled": "use_controls_body",
        }
    else:
        expected = {
            "supported": "body_generates_use",
            "controls": "use_controls_body",
            "controlled": "body_controls_use",
        }
    return code == expected[signal]


def _rule_matches(rule: dict[str, Any], signals: set[str]) -> bool:
    required = set(rule.get("all", []))
    alternatives = set(rule.get("any", []))
    forbidden = set(rule.get("none", []))
    return (
        required.issubset(signals)
        and (not alternatives or bool(alternatives & signals))
        and not bool(forbidden & signals)
    )


def _evaluate_stage(
    trigram: str,
    stage: str,
    signals: set[str],
    definitions: dict[str, str],
) -> dict[str, Any]:
    entry = load_conditional_trigram_meanings()["trigrams"][trigram]
    scores = {item["name"]: 0.0 for item in entry["possible_meanings"]}
    matched: list[dict[str, Any]] = []
    for rule in entry["rules"]:
        if not _rule_matches(rule, signals):
            continue
        priority = int(rule["priority"])
        for order, meaning in enumerate(rule["prefer"]):
            scores[meaning] += priority - order * 0.1
        for meaning in rule.get("suppress", []):
            scores[meaning] -= priority * 0.55
        used = list(dict.fromkeys(rule.get("all", []) + rule.get("any", [])))
        matched.append(
            {
                "rule_id": rule["id"],
                "priority": priority,
                "condition": rule["condition_text"],
                "preferred_meanings": list(rule["prefer"]),
                "suppressed_meanings": list(rule.get("suppress", [])),
                "football_reading": rule["football_reading"],
                "matched_evidence": [
                    {"signal": signal, "meaning": definitions[signal]}
                    for signal in used
                    if signal in signals
                ],
            }
        )
    matched.sort(key=lambda item: (-item["priority"], item["rule_id"]))
    ordered = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    if not matched:
        ordered = [(item["name"], 0.0) for item in entry["possible_meanings"]]
    football_by_name = {item["name"]: item["football"] for item in entry["possible_meanings"]}
    prioritized = [
        {
            "rank": rank,
            "meaning": name,
            "rule_score": round(score, 1),
            "football": football_by_name[name],
        }
        for rank, (name, score) in enumerate(ordered[:3], 1)
    ]
    return {
        "stage": stage,
        "trigram": trigram,
        "classical_core": entry["classical_core"],
        "possible_meanings": list(entry["possible_meanings"]),
        "active_signals": [
            {"signal": signal, "meaning": definitions[signal]}
            for signal in sorted(signals)
        ],
        "matched_rules": matched,
        "prioritized_meanings": prioritized,
        "primary_summary": "、".join(item["meaning"] for item in prioritized),
        "rule_note": "分數只用來排序同一卦的候選義項，不是機率、進球數或勝負信心。",
    }


def _path_signals(
    result: HexagramResult,
    seasonal: dict[str, Any],
    najia: dict[str, Any],
    side: str,
) -> tuple[set[str], dict[str, Any]]:
    is_body = side == "body"
    before = result.body_gua if is_body else result.use_gua
    after = result.changed_body_gua if is_body else result.changed_use_gua
    opponent_before = result.use_gua if is_body else result.body_gua
    opponent_after = result.changed_use_gua if is_body else result.changed_body_gua
    strength_before = seasonal["body_before" if is_body else "use_before"]
    strength_after = seasonal["body_after" if is_body else "use_after"]
    opponent_strength_before = seasonal["use_before" if is_body else "body_before"]
    before_score = _relation_score(result.relation_code, side)
    after_score = _relation_score(result.changed_relation_code, side)
    moving_side = (result.moving_side == "體方") == is_body
    moving_line = najia["main_hexagram"]["lines"][result.moving_line - 1]
    moving_void = bool(moving_line["is_void"])
    moving_month_broken = (
        branch_relation(
            str(moving_line["branch"]),
            str(najia["day_cycle"]["month_branch"]),
        )
        == "六沖"
    )
    interactions = najia["main_hexagram"]["branch_interactions"]
    clashes = sum(item["relation"] == "六沖" for item in interactions)
    combinations = sum(item["relation"] == "六合" for item in interactions)
    path_trigrams = (
        result.body_gua,
        result.use_gua,
        result.mutual_lower_gua,
        result.mutual_upper_gua,
        result.changed_body_gua,
        result.changed_use_gua,
    )
    path_hexagrams = (
        result.main_hexagram,
        result.mutual_hexagram,
        result.changed_hexagram,
    )
    breakthrough_count = sum(item in HIGH_ENERGY_TRIGRAMS for item in path_trigrams)
    breakthrough_count += sum(
        any(marker in name for marker in BREAKTHROUGH_HEXAGRAM_MARKERS)
        for name in path_hexagrams
    )

    signals: set[str] = set()
    if before == after:
        signals.add("unchanged")
    if moving_side:
        signals.add("moving_side")
        if moving_void or moving_month_broken:
            signals.add("moving_void_or_broken")
        else:
            signals.add("moving_effective")
        signals.add("early_or_middle_move" if result.moving_line <= 4 else "late_move")
    if strength_before in {"旺", "相"}:
        signals.add("strong_before")
    if strength_after in {"旺", "相"}:
        signals.add("strong_after")
    if strength_after in {"囚", "死"}:
        signals.add("weak_after")
    if _relation_signal(result.relation_code, side, "supported"):
        signals.add("supported_before")
    if _relation_signal(result.changed_relation_code, side, "supported"):
        signals.add("supported_after")
    if _relation_signal(result.changed_relation_code, side, "controls"):
        signals.add("controls_opponent_after")
    if _relation_signal(result.changed_relation_code, side, "controlled"):
        signals.add("controlled_after")
    if after_score > before_score:
        signals.add("relation_improves")
    elif after_score < before_score:
        signals.add("relation_worsens")
    if before_score > 0 or STRENGTH_RANK[strength_before] - STRENGTH_RANK[opponent_strength_before] >= 2:
        signals.add("prior_advantage")
    if breakthrough_count == 0:
        signals.add("low_breakthrough_path")
    if breakthrough_count >= 2:
        signals.add("high_breakthrough_path")
    if (
        opponent_before in HIGH_ENERGY_TRIGRAMS
        or opponent_after in HIGH_ENERGY_TRIGRAMS
        or any(marker in name for name in path_hexagrams for marker in BREAKTHROUGH_HEXAGRAM_MARKERS)
    ):
        signals.add("opponent_breakthrough_signal")
    if clashes >= 2:
        signals.add("many_clashes")
    if combinations >= 2:
        signals.add("many_combinations")
    if result.body_gua == result.use_gua:
        signals.add("same_trigram_opposition")

    return signals, {
        "side": "體方" if is_body else "用方",
        "party_name": result.body_name if is_body else result.use_name,
        "before_trigram": before,
        "after_trigram": after,
        "opponent_before_trigram": opponent_before,
        "opponent_after_trigram": opponent_after,
        "strength_before": strength_before,
        "strength_after": strength_after,
        "relation_before": result.relation,
        "relation_after": result.changed_relation,
        "moving_line_on_side": moving_side,
        "moving_line_void": moving_void if moving_side else False,
        "moving_line_month_broken": moving_month_broken if moving_side else False,
        "clash_count": clashes,
        "combination_count": combinations,
        "breakthrough_signal_count": breakthrough_count,
    }


def _build_side_path(
    result: HexagramResult,
    seasonal: dict[str, Any],
    najia: dict[str, Any],
    side: str,
    definitions: dict[str, str],
) -> dict[str, Any]:
    signals, facts = _path_signals(result, seasonal, najia, side)
    before = str(facts["before_trigram"])
    after = str(facts["after_trigram"])
    stages: list[dict[str, Any]] = []
    if before == after:
        stages.append(_evaluate_stage(before, "保持不變", set(signals), definitions))
    else:
        before_signals = set(signals) | {"changed_from"}
        if after in HIGH_ENERGY_TRIGRAMS:
            before_signals.add("changed_to_high_energy")
        after_signals = set(signals) | {"changed_into"}
        if before in HIGH_ENERGY_TRIGRAMS:
            after_signals.add("changed_from_high_energy")
        stages.append(_evaluate_stage(before, "變前", before_signals, definitions))
        stages.append(_evaluate_stage(after, "變後", after_signals, definitions))
    return {
        **facts,
        "transition": f"{before}→{after}",
        "stages": stages,
        "path_summary": " → ".join(
            f"{stage['trigram']}（{stage['primary_summary']}）"
            for stage in stages
        ),
    }


def build_conditional_meanings(
    result: HexagramResult,
    seasonal: dict[str, Any],
    najia: dict[str, Any],
) -> dict[str, Any]:
    payload = load_conditional_trigram_meanings()
    definitions = payload["signal_definitions"]
    return {
        "version": payload["version"],
        "scope": payload["scope"],
        "evaluation_boundary": payload["evaluation_boundary"],
        "body_path": _build_side_path(result, seasonal, najia, "body", definitions),
        "use_path": _build_side_path(result, seasonal, najia, "use", definitions),
        "whole_line_note": "條件匹配沿體用變前、動爻與變後連續閱讀；同一卦的正反義由訊號觸發，不依已知賽果臨時選義。",
    }


__all__ = ["build_conditional_meanings"]
