from pathlib import Path

import pandas as pd

from config import AppConfig
from evaluation import controlled_final_scores
from models import AIAnalysis, HexagramResult, RulePrediction
from storage_v32 import CaseStore
from case_memory import retrieve_similar_cases


def rule_prediction():
    return RulePrediction(
        scores=[(0, 0), (0, 1), (1, 1)],
        expected_body_goals=0.5,
        expected_use_goals=1.0,
        direction="平局或一球差拉鋸",
        confidence=0.4,
        reasons=[],
        score_grid=[
            {"score": score, "weight": 1.0}
            for score in ["0-0", "0-1", "1-1", "1-0", "1-2", "2-1"]
        ],
    )


def ai(scores):
    return AIAnalysis(
        ok=True,
        provider="github_models",
        model="test-model",
        direction="用方勝",
        scores=scores,
        confidences=[0.4, 0.3, 0.2],
        score_reasons=["a", "b", "c"],
        overall_reasoning="",
        risk_warning="",
    )


def test_ai_cannot_invent_or_flip_direction_with_too_few_cases():
    scores, metadata = controlled_final_scores(
        rule_prediction(),
        ai([(3, 3), (0, 1), (1, 1)]),
        similar_case_count=1,
    )
    assert scores[0] == (0, 0)
    assert metadata["direction_guard"] is True
    assert (3, 3) not in scores


def test_case_memory_reads_v32_final_scores_and_skips_unconfirmed():
    result = HexagramResult(
        match_name="新賽",
        body_team="甲",
        use_team="乙",
        body_count=8,
        use_count=5,
        total_count=18,
        body_gua="坤",
        use_gua="巽",
        body_number=8,
        use_number=5,
        body_element="土",
        use_element="木",
        main_hexagram="風地觀",
        mutual_hexagram="山地剝",
        moving_line=3,
        moving_side="體方",
        moving_layer="下卦",
        changed_hexagram="風山漸",
        changed_body_gua="艮",
        changed_use_gua="巽",
        body_transition="坤->艮",
        use_transition="巽->巽",
        relation_code="use_controls_body",
        relation="用剋體",
        relation_detail="",
        moving_detail="",
        structural_tags=["體用:use_controls_body"],
    )
    casebook = pd.DataFrame(
        [
            {
                "案例ID": "A",
                "比賽": "舊賽",
                "體卦": "坤",
                "用卦": "巽",
                "體卦五行": "土",
                "用卦五行": "木",
                "體用代碼": "use_controls_body",
                "本卦": "風地觀",
                "互卦": "山地剝",
                "動爻": 3,
                "動爻位置": "體方",
                "變卦": "風山漸",
                "體方轉卦": "坤->艮",
                "用方轉卦": "巽->巽",
                "最終首選比分": "0-0",
                "最終第二選比分": "0-1",
                "最終第三選比分": "1-1",
                "實際比分": "0-0",
                "校準原因": "收束鏈需保留0-0",
                "校準狀態": "已確認",
                "案例品質": "高",
            },
            {
                "案例ID": "B",
                "比賽": "未確認",
                "實際比分": "2-2",
                "校準原因": "不應使用",
                "校準狀態": "待確認",
            },
        ]
    )
    cases = retrieve_similar_cases(result, casebook, top_k=5)
    assert len(cases) == 1
    assert cases[0].predicted_scores == "0-0/0-1/1-1"


def test_postmatch_update_persists_separate_rule_ai_metrics(tmp_path: Path):
    config = AppConfig(data_dir=tmp_path / "data", reports_dir=tmp_path / "reports")
    store = CaseStore(config)
    store.save(
        pd.DataFrame(
            [
                {
                    "案例ID": "CASE-1",
                    "比賽": "甲 vs 乙",
                    "規則首選比分": "0-0",
                    "規則第二選比分": "0-1",
                    "規則第三選比分": "1-1",
                    "AI首選比分": "0-1",
                    "AI第二選比分": "1-1",
                    "AI第三選比分": "0-0",
                    "最終首選比分": "0-0",
                    "最終第二選比分": "0-1",
                    "最終第三選比分": "1-1",
                }
            ]
        )
    )
    updated, _ = store.update_postmatch(
        "CASE-1",
        "0-0",
        "人工確認",
        "摘要",
        "已確認",
        "高",
    )
    row = updated.iloc[0]
    assert row["規則首選命中"] == "是"
    assert row["AI首選命中"] == "否"
    assert row["AI是否改善"] == "惡化"
    assert row["校準狀態"] == "已確認"
