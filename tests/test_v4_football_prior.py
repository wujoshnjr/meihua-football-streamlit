from __future__ import annotations

import json

from ai_reasoner_v33 import build_prediction_prompt
from football_prior import build_football_prior
from meihua_engine import calculate_match_hexagram
from models import HexagramResult, MatchInput
from score_engine import predict_scores


def match(body_rating: float, use_rating: float, confidence: float = 0.8) -> MatchInput:
    return MatchInput(
        match_name="甲 vs 乙",
        body_team="甲",
        use_team="乙",
        body_text="甲方依靠整體組織、邊路推進與穩定防守。",
        use_text="乙方採取緊密防守、快速反擊與定位球進攻。",
        full_text="本場只判斷九十分鐘，雙方各有攻守優勢，勝負關鍵在轉換效率與禁區完成度。",
        body_strength_rating=body_rating,
        use_strength_rating=use_rating,
        prior_confidence=confidence,
        venue="中立場",
    )


def closed_hypothesis_result() -> HexagramResult:
    return HexagramResult(
        match_name="甲 vs 乙",
        body_team="甲",
        use_team="乙",
        body_count=8,
        use_count=7,
        total_count=6,
        body_gua="坤",
        use_gua="艮",
        body_number=8,
        use_number=7,
        body_element="土",
        use_element="土",
        main_hexagram="山地剝",
        mutual_hexagram="坤為地",
        moving_line=6,
        moving_side="用方",
        moving_layer="上卦",
        changed_hexagram="坤為地",
        changed_body_gua="坤",
        changed_use_gua="坤",
        body_transition="坤->坤",
        use_transition="艮->坤",
        relation_code="equal",
        relation="比和",
        relation_detail="",
        moving_detail="",
        structural_tags=[],
    )


def test_football_prior_is_independent_and_symmetric_when_neutral() -> None:
    prior = build_football_prior(match(50, 50, 1.0))
    assert prior["body_lambda"] == prior["use_lambda"]
    assert prior["body_lambda"] + prior["use_lambda"] == prior["total_lambda"]
    assert prior["method"] == "football-prior-v1"


def test_large_credible_gap_retains_high_score_tail() -> None:
    prediction = predict_scores(closed_hypothesis_result(), match(92, 18, 0.95))
    assert prediction.football_expected_body_goals > prediction.football_expected_use_goals
    assert prediction.football_prior["five_plus_probability"] > 0.10
    assert len(prediction.score_grid) == 121
    assert any(int(row["body_goals"]) >= 7 for row in prediction.score_grid)


def test_hexagram_adjustment_is_bounded_and_single_case_rule_is_not_applied() -> None:
    prediction = predict_scores(closed_hypothesis_result(), match(55, 55, 0.8))
    assert 0.75 <= prediction.hexagram_body_multiplier <= 1.25
    assert 0.75 <= prediction.hexagram_use_multiplier <= 1.25
    hypothesis = next(rule for rule in prediction.matched_rules if rule["id"] == "CAL-001")
    assert hypothesis["status"] == "hypothesis"
    assert hypothesis["applied"] is False
    assert hypothesis["applied_scale"] == 0.0


def test_prematch_ai_does_not_receive_hypothesis_source_score_or_effects() -> None:
    current_match = match(55, 55, 0.8)
    result = closed_hypothesis_result()
    prediction = predict_scores(result, current_match)
    _, user_prompt = build_prediction_prompt(current_match, result, prediction, [])
    payload = json.loads(user_prompt)
    hypothesis = next(rule for rule in payload["rule_engine_prediction"]["matched_rules"] if rule["id"] == "CAL-001")
    assert hypothesis["applied"] is False
    assert "source_case" not in hypothesis
    assert "effects" not in hypothesis


def test_all_trigram_pairs_and_moving_lines_respect_probability_contract() -> None:
    for body_count in range(1, 9):
        for use_count in range(1, 9):
            for moving_line in range(1, 7):
                current_match = MatchInput(
                    match_name="全組合測試",
                    body_team="甲",
                    use_team="乙",
                    body_text="甲" * body_count,
                    use_text="乙" * use_count,
                    full_text="中" * moving_line,
                    body_strength_rating=65,
                    use_strength_rating=55,
                    prior_confidence=0.7,
                )
                result = calculate_match_hexagram(current_match)
                prediction = predict_scores(result, current_match)
                assert 0.75 <= prediction.hexagram_body_multiplier <= 1.25
                assert 0.75 <= prediction.hexagram_use_multiplier <= 1.25
                assert len(prediction.scores) == len(set(prediction.scores)) == 3
                assert abs(sum(float(row["probability"]) for row in prediction.score_grid) - 1.0) < 1e-5
