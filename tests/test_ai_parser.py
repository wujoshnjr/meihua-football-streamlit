import json

from ai_reasoner_v33 import (
    DELIBERATION_SCHEMA,
    PREDICTION_SCHEMA,
    _parse_json_object,
    _validate_deliberation,
    build_deliberation_prompt,
    build_prediction_prompt,
    run_ai_prediction,
)
from meihua_engine import calculate_match_hexagram
from models import MatchInput
from score_engine import predict_scores


def test_parse_json_fenced_content():
    payload = _parse_json_object('```json\n{"result_direction":"體方勝"}\n```')
    assert payload["result_direction"] == "體方勝"


def _fixture():
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
    return match, result, prediction


def test_v42_first_stage_is_blind_to_scores_and_numeric_prior() -> None:
    match, result, prediction = _fixture()
    system_prompt, user_prompt = build_deliberation_prompt(match, result, prediction)
    payload = json.loads(user_prompt)

    assert DELIBERATION_SCHEMA["name"] == "meihua_blind_hexagram_deliberation_v1"
    assert payload["phase"] == "blind_semantic_hexagram_deliberation"
    assert "比分候選" in system_prompt
    assert "allowed_score_candidates" not in user_prompt
    assert "score_grid" not in user_prompt
    assert "football_prior" not in user_prompt
    assert "score_patterns" not in user_prompt
    assert "attack_rating" not in user_prompt
    assert "defense_rating" not in user_prompt
    assert "dynamics_score" not in user_prompt
    assert "total_goal_targets" not in user_prompt
    assert "primary_interpretation" not in user_prompt
    assert "body_count" not in user_prompt
    assert "1-1" not in system_prompt + user_prompt
    assert "2-1" not in system_prompt + user_prompt


def test_v42_second_stage_receives_deliberation_without_rule_ranking() -> None:
    match, result, prediction = _fixture()
    deliberation = {
        "thesis": "先看主局如何被動爻改寫，再判破門是否成立。",
        "primary_scenario": {"name": "語義主線"},
    }
    system_prompt, user_prompt = build_prediction_prompt(
        match,
        result,
        prediction,
        [],
        deliberation,
    )
    payload = json.loads(user_prompt)
    required = set(PREDICTION_SCHEMA["schema"]["required"])

    assert {
        "match_script_summary",
        "scoring_channel_analysis",
        "energy_ownership_analysis",
        "total_goals_reasoning",
        "score_allocation_reasoning",
        "selected_scenario_names",
    }.issubset(required)
    assert "第一階段" in system_prompt
    assert payload["phase"] == "football_calibration_and_score_decision"
    assert payload["blind_hexagram_deliberation"]["thesis"] == deliberation["thesis"]
    assert payload["allowed_score_candidates"]
    assert "score_grid" not in user_prompt
    assert "rule_engine_prediction" not in user_prompt
    totals = [item["total_goals"] for item in payload["allowed_score_candidates"]]
    assert totals == sorted(totals)


def test_run_ai_prediction_executes_blind_deliberation_before_score_decision() -> None:
    match, result, prediction = _fixture()

    class FakeClient:
        model = "fake/two-stage"

        def __init__(self) -> None:
            self.calls: list[str] = []

        def infer_json(self, system_prompt, user_prompt, json_schema=None):
            name = json_schema["name"]
            self.calls.append(name)
            if name == DELIBERATION_SCHEMA["name"]:
                assert "allowed_score_candidates" not in user_prompt
                return {
                    "thesis": "AI盲解主線：先看同數結構是對消或共振。",
                    "counter_reading": "若轉象形成真實破口，對消可以改讀為共振。",
                }, {"stage": "blind"}
            scores = [f"{body}-{use}" for body, use in prediction.scores]
            return {
                "result_direction": "平局",
                "score_candidates": [
                    {"score": score, "confidence": 0.5, "reason": "由盲解劇本再經足球先驗校準。"}
                    for score in scores
                ],
                "selected_scenario_names": ["AI盲解主線"],
            }, {"stage": "decision"}

    client = FakeClient()
    analysis = run_ai_prediction(client, match, result, prediction, [])

    assert analysis.ok is True
    assert client.calls == [DELIBERATION_SCHEMA["name"], PREDICTION_SCHEMA["name"]]
    assert analysis.hexagram_deliberation["thesis"].startswith("AI盲解主線")
    assert analysis.hexagram_deliberation["blind_to_scores"] is True
    assert analysis.hexagram_deliberation["model"] == "fake/two-stage"
    assert analysis.selected_scenario_names == ["AI盲解主線"]
    assert set(analysis.raw_response) == {"deliberation", "decision"}


def test_deliberation_validator_removes_any_exact_score_anchor() -> None:
    fallback = {
        "primary_scenario": {},
        "alternative_scenario": {},
    }
    validated = _validate_deliberation(
        {
            "thesis": "不應在盲解階段偷渡2-1。",
            "counter_reading": "另一分支也不能先寫0:0。",
            "numeric_symbolism": [
                {
                    "symbol": "3-2",
                    "supported_meaning": "只能談能量，不是1-1。",
                    "rejected_shortcut": "禁止比分錨定。",
                }
            ],
        },
        fallback,
    )
    rendered = json.dumps(validated, ensure_ascii=False)

    assert "2-1" not in rendered
    assert "0:0" not in rendered
    assert "3-2" not in rendered
    assert "1-1" not in rendered
    assert "精確比分留待第二階段" in rendered
