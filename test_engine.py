from meihua_engine import calculate_match_hexagram, count_symbols
from models import MatchInput
from score_engine import predict_scores


def test_count_symbols_mixed_language():
    text = "阿根廷 Jonathan David Aït-Nouri 2026，3-2"
    assert count_symbols(text) == 9


def test_hexagram_calculation_known_counts():
    match = MatchInput(
        match_name="測試",
        body_team="體方",
        use_team="用方",
        body_text="天地玄黃宇宙洪荒",  # 8 → 坤
        use_text="天",               # 1 → 乾
        full_text="天地玄黃宇宙",    # 6 → 六爻動
    )
    result = calculate_match_hexagram(match)
    assert result.body_gua == "坤"
    assert result.use_gua == "乾"
    assert result.main_hexagram == "天地否"
    assert result.mutual_hexagram == "風山漸"
    assert result.moving_line == 6
    assert result.moving_side == "用方"
    assert result.use_transition == "乾->兌"
    assert result.changed_hexagram == "澤地萃"


def test_rule_prediction_returns_three_unique_scores():
    match = MatchInput(
        match_name="測試二",
        body_team="甲",
        use_team="乙",
        body_text="甲乙丙丁戊己庚辛壬癸",
        use_text="甲乙丙丁戊己庚",
        full_text="甲乙丙丁戊己庚辛壬癸子丑寅",
    )
    result = calculate_match_hexagram(match)
    prediction = predict_scores(result)
    assert len(prediction.scores) == 3
    assert len(set(prediction.scores)) == 3
    assert all(0 <= a <= 5 and 0 <= b <= 5 for a, b in prediction.scores)
