from __future__ import annotations

import pandas as pd

from evaluation import evaluate_predictions, outcome_brier, outcome_log_loss
from metrics_dashboard import build_metrics_table


def test_missing_ai_prediction_is_not_counted_as_a_miss() -> None:
    metrics = evaluate_predictions([], "1-0")
    assert metrics["first_hit"] == ""
    assert metrics["outcome_hit"] == ""


def test_legacy_scores_are_evaluated_without_claiming_v4_baseline() -> None:
    casebook = pd.DataFrame(
        [
            {
                "案例ID": "LEGACY-1",
                "比賽": "甲 vs 乙",
                "首選比分": "1-0",
                "第二選比分": "1-1",
                "第三選比分": "2-0",
                "實際比分": "1-0",
                "校準狀態": "已確認",
            }
        ]
    )
    metrics = build_metrics_table(casebook)
    assert metrics.iloc[0]["規則首選命中"] == "是"
    assert metrics.iloc[0]["足球基線首選命中"] == ""
    assert metrics.iloc[0]["系統版本"] == "legacy"


def test_probability_scores_reward_better_calibration() -> None:
    good = {"體方勝": 0.75, "平局": 0.15, "用方勝": 0.10}
    bad = {"體方勝": 0.10, "平局": 0.15, "用方勝": 0.75}
    assert outcome_brier(good, "2-1") < outcome_brier(bad, "2-1")
    assert outcome_log_loss(good, "2-1") < outcome_log_loss(bad, "2-1")

