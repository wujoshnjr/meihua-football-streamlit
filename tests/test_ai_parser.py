import json

from ai_reasoner_v33 import PREDICTION_SCHEMA, _parse_json_object, build_prediction_prompt
from meihua_engine import calculate_match_hexagram
from models import MatchInput
from score_engine import predict_scores


def test_parse_json_fenced_content():
    payload = _parse_json_object('```json\n{"result_direction":"體方勝"}\n```')
    assert payload["result_direction"] == "體方勝"


def test_v41_prompt_requires_continuous_script_reasoning() -> None:
    match = MatchInput(
        match_name="甲 vs 乙",
        body_team="甲",
        use_team="乙",
        body_text="甲甲",
        use_text="乙乙",
        full_text="中中",
    )
    result = calculate_match_hexagram(match)
    prediction = predict_scores(result, match)
    system_prompt, user_prompt = build_prediction_prompt(match, result, prediction, [])
    payload = json.loads(user_prompt)
    required = set(PREDICTION_SCHEMA["schema"]["required"])

    assert {
        "match_script_summary",
        "scoring_channel_analysis",
        "energy_ownership_analysis",
        "total_goals_reasoning",
        "score_allocation_reasoning",
    }.issubset(required)
    assert "同卦同數不可固定判平或固定判大球" in system_prompt
    assert payload["rule_engine_prediction"]["hexagram_script"]["candidate_scores"]
