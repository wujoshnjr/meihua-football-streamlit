from __future__ import annotations

from collections import Counter

import pytest

from evaluation import candidate_scores
from meihua_engine import calculate_match_hexagram
from models import MatchInput, RulePrediction
from score_engine import predict_scores


def prediction(
    body_count: int,
    use_count: int,
    moving_line: int,
    body_rating: float = 50,
    use_rating: float = 50,
    confidence: float = 0.5,
) -> RulePrediction:
    match = MatchInput(
        match_name="甲 vs 乙",
        body_team="甲",
        use_team="乙",
        body_text="甲" * body_count,
        use_text="乙" * use_count,
        full_text="中" * moving_line,
        body_strength_rating=body_rating,
        use_strength_rating=use_rating,
        prior_confidence=confidence,
        venue="中立場",
    )
    return predict_scores(calculate_match_hexagram(match), match)


def score_set(script: dict[str, object]) -> set[str]:
    values = script.get("candidate_scores", [])
    assert isinstance(values, list)
    return {str(item["score"]) for item in values if isinstance(item, dict)}


def test_double_qian_without_channel_is_mirror_cancellation() -> None:
    result = prediction(1, 1, 2)
    script = result.hexagram_script

    assert script["mirror_mode"] == "鏡像對消"
    assert script["zero_goal_gate"] is True
    assert script["scoring_channel_score"] < script["closure_score"]
    assert result.scores[0] == (0, 0)


def test_double_dui_open_transition_uses_same_number_resonance() -> None:
    result = prediction(2, 2, 2, 75, 45, 0.85)
    script = result.hexagram_script
    numeric_values = {item["value"] for item in script["numeric_signals"]}

    assert script["mirror_mode"] == "同數共振"
    assert script["high_score_gate"] is True
    assert 6 in numeric_values
    assert any(sum(map(int, score.split("-"))) == 6 for score in score_set(script))
    assert sum(result.scores[0]) == 6


def test_dun_gou_fou_closure_opens_zero_goal_gate() -> None:
    result = prediction(7, 1, 3)
    script = result.hexagram_script

    assert script["zero_goal_gate"] is True
    assert script["scoring_channel_score"] < 38
    assert "0-0" in score_set(script)
    assert result.scores[0] == (0, 0)


def test_relation_reversal_keeps_both_late_comeback_branches() -> None:
    result = prediction(8, 6, 6, 60, 60, 0.7)
    script = result.hexagram_script
    scores = score_set(script)

    assert script["high_score_gate"] is True
    assert script["zero_goal_gate"] is False
    assert script["volatility_score"] >= 64
    assert {"2-3", "3-2"}.issubset(scores)


def test_high_open_joint_amplification_retains_three_three() -> None:
    result = prediction(3, 2, 5, 55, 55, 0.7)
    script = result.hexagram_script

    assert script["environment"] == "爆發／崩盤風險"
    assert script["btts_signal"] is True
    assert "3-3" in score_set(script)


@pytest.mark.parametrize(
    ("body_count", "use_count", "moving_line", "body_rating", "use_rating", "confidence"),
    [
        (3, 2, 1, 88, 28, 0.90),  # 離／兌，體方早段轉艮
        (4, 8, 5, 92, 18, 0.95),  # 震／坤，用方後段轉坎
    ],
)
def test_large_mismatch_and_one_way_energy_retain_rout_tail(
    body_count: int,
    use_count: int,
    moving_line: int,
    body_rating: float,
    use_rating: float,
    confidence: float,
) -> None:
    result = prediction(body_count, use_count, moving_line, body_rating, use_rating, confidence)
    script = result.hexagram_script

    assert script["rout_side"] == "體方"
    assert script["zero_goal_gate"] is False
    assert max(script["total_goal_targets"]) >= 5
    assert any(sum(map(int, score.split("-"))) >= 5 for score in score_set(script))
    assert sum(result.scores[0]) >= 5


def test_full_hexagram_space_no_longer_collapses_to_common_scores() -> None:
    first_scores: Counter[tuple[int, int]] = Counter()
    high_score_firsts = 0
    zero_score_firsts = 0

    for body_count in range(1, 9):
        for use_count in range(1, 9):
            for moving_line in range(1, 7):
                result = prediction(body_count, use_count, moving_line)
                first = result.scores[0]
                first_scores[first] += 1
                high_score_firsts += int(sum(first) >= 5)
                zero_score_firsts += int(first == (0, 0))
                assert abs(sum(float(row["probability"]) for row in result.score_grid) - 1.0) < 1e-6

    assert sum(first_scores.values()) == 384
    assert len(first_scores) >= 10
    assert first_scores[(1, 1)] + first_scores[(2, 1)] < 192
    assert 0 < high_score_firsts < 96
    assert zero_score_firsts > 0


def test_script_archetypes_are_available_to_ai_candidate_pool() -> None:
    result = prediction(2, 2, 2, 75, 45, 0.85)
    pool = {f"{body}-{use}" for body, use in candidate_scores(result, 18)}
    script_scores = score_set(result.hexagram_script)

    assert len(pool & script_scores) >= 3
    assert any(sum(map(int, score.split("-"))) >= 5 for score in pool)
