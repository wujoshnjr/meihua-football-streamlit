from __future__ import annotations

from decision_control_v33 import candidate_scores, controlled_final_scores, outcome
from models import AIAnalysis, HexagramResult, MatchInput, RulePrediction
from score_engine import predict_scores


def france_morocco_like_result() -> HexagramResult:
    return HexagramResult(
        match_name="體方 vs 用方",
        body_team="體方",
        use_team="用方",
        body_count=3,
        use_count=8,
        total_count=1,
        body_gua="離",
        use_gua="坤",
        body_number=3,
        use_number=8,
        body_element="火",
        use_element="土",
        main_hexagram="地火明夷",
        mutual_hexagram="雷水解",
        moving_line=1,
        moving_side="體方",
        moving_layer="下卦",
        changed_hexagram="地山謙",
        changed_body_gua="艮",
        changed_use_gua="坤",
        body_transition="離->艮",
        use_transition="坤->坤",
        relation_code="body_generates_use",
        relation="體生用：體方能量流向用方",
        relation_detail="體生用只代表外洩風險。",
        moving_detail="初爻在體方。",
        structural_tags=[],
    )


def test_body_generates_use_does_not_force_all_use_wins() -> None:
    match = MatchInput(
        match_name="體方 vs 用方",
        body_team="體方",
        use_team="用方",
        body_text="體方具備更強的整體實力、攻擊核心與淘汰賽經驗。",
        use_text="用方防守完整並擅長反擊，但整體進攻創造力較低。",
        full_text="雙方進行九十分鐘淘汰賽，體方整體實力較高，用方以防守反擊應戰。",
        body_strength_rating=72,
        use_strength_rating=58,
        prior_confidence=0.75,
        venue="中立場",
    )
    prediction = predict_scores(france_morocco_like_result(), match)
    assert prediction.method == "score-engine-v4.2.0"
    assert any(body > use for body, use in prediction.scores)
    assert not all(body < use for body, use in prediction.scores)
    assert any("體生用視為外洩與反擊風險" in item for item in prediction.reasons)
    assert 0.75 <= prediction.hexagram_body_multiplier <= 1.25
    assert 0.75 <= prediction.hexagram_use_multiplier <= 1.25


def test_balanced_candidate_pool_contains_all_outcomes() -> None:
    prediction = predict_scores(france_morocco_like_result())
    pool = candidate_scores(prediction, 15)
    directions = {outcome(f"{body}-{use}") for body, use in pool}
    assert directions == {"體方勝", "平局", "用方勝"}


def artificial_rule_prediction() -> RulePrediction:
    grid = [
        {"score": "0-1", "weight": 0.20, "rank": 1},
        {"score": "0-0", "weight": 0.18, "rank": 2},
        {"score": "1-1", "weight": 0.16, "rank": 3},
        {"score": "1-0", "weight": 0.15, "rank": 4},
        {"score": "2-0", "weight": 0.12, "rank": 5},
        {"score": "0-2", "weight": 0.10, "rank": 6},
        {"score": "2-1", "weight": 0.09, "rank": 7},
        {"score": "1-2", "weight": 0.08, "rank": 8},
        {"score": "2-2", "weight": 0.07, "rank": 9},
        {"score": "3-1", "weight": 0.05, "rank": 10},
        {"score": "1-3", "weight": 0.04, "rank": 11},
        {"score": "3-0", "weight": 0.03, "rank": 12},
    ]
    return RulePrediction(
        scores=[(0, 1), (0, 0), (1, 1)],
        expected_body_goals=0.8,
        expected_use_goals=1.1,
        direction="用方勝",
        confidence=0.35,
        reasons=[],
        score_grid=grid,
        outcome_probabilities={"體方勝": 0.35, "平局": 0.30, "用方勝": 0.35},
    )


def test_weak_ai_cannot_flip_direction() -> None:
    rule = artificial_rule_prediction()
    ai = AIAnalysis(
        ok=True,
        provider="github_models",
        model="test",
        direction="體方勝",
        scores=[(2, 0), (1, 0), (2, 1)],
        confidences=[0.4, 0.3, 0.2],
        score_reasons=["", "", ""],
        overall_reasoning="",
        risk_warning="",
        body_strength_score=58,
        use_strength_score=52,
        evidence_quality=0.45,
        direction_confidence=0.50,
    )
    final, metadata = controlled_final_scores(rule, ai, similar_case_count=1)
    assert final[0] == (0, 1)
    assert metadata["mode"] == "direction_guard"


def test_strong_evidence_can_correct_direction_inside_pool() -> None:
    rule = artificial_rule_prediction()
    ai = AIAnalysis(
        ok=True,
        provider="github_models",
        model="test",
        direction="體方勝",
        scores=[(2, 0), (1, 0), (2, 1)],
        confidences=[0.72, 0.60, 0.52],
        score_reasons=["", "", ""],
        overall_reasoning="",
        risk_warning="",
        body_strength_score=76,
        use_strength_score=56,
        evidence_quality=0.82,
        direction_confidence=0.78,
    )
    final, metadata = controlled_final_scores(rule, ai, similar_case_count=1)
    assert final[0] == (2, 0)
    assert metadata["mode"] == "strong_evidence_correction_v4"
