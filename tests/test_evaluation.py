from __future__ import annotations

from datetime import timedelta

import pytest

from qimen.engine import cast_qimen
from qimen.evaluation import (
    aggregate_prediction_evaluations,
    compare_prediction_models,
    evaluate_prediction,
    evaluate_scenarios,
    lock_prediction,
    lock_scenarios,
    qimen_activation_gate,
)
from qimen.football import interpret_football
from qimen.prediction import PrematchModelInput, TeamForm, build_prediction


def test_scenarios_must_be_locked_prematch(calendar_context):
    board = cast_qimen(calendar_context.local_datetime, calendar_context.timezone_name, calendar=calendar_context)
    reading = interpret_football(board)
    with pytest.raises(ValueError, match="開賽前"):
        lock_scenarios("TEST", calendar_context.local_datetime, calendar_context.local_datetime, reading)


def test_qualitative_top_k_evaluation(calendar_context):
    board = cast_qimen(calendar_context.local_datetime, calendar_context.timezone_name, calendar=calendar_context)
    reading = interpret_football(board)
    locked = lock_scenarios(
        "TEST", calendar_context.local_datetime,
        calendar_context.local_datetime - timedelta(hours=8), reading,
    )
    result = evaluate_scenarios(locked, [reading.scenarios[0].title], top_k=3)
    assert result["precision_at_k"] == pytest.approx(1 / 3)
    assert "不回推出勝率" in result["note"]


def _prediction(calendar_context):
    board = cast_qimen(
        calendar_context.local_datetime,
        calendar_context.timezone_name,
        calendar=calendar_context,
    )
    reading = interpret_football(board)
    model_input = PrematchModelInput(
        home=TeamForm(10, 1.8, 1.1),
        away=TeamForm(10, 1.1, 1.6),
        data_as_of=calendar_context.local_datetime - timedelta(days=1),
        data_source="test-fixture",
    )
    return build_prediction(model_input, board, reading)


def test_locked_prediction_scores_1x2_and_exact_score(calendar_context):
    prediction = _prediction(calendar_context)
    locked = lock_prediction(
        "JARVIS-TEST",
        calendar_context.local_datetime,
        calendar_context.local_datetime - timedelta(hours=8),
        prediction,
    )
    result = evaluate_prediction(locked, 2, 1)
    assert result["actual_result"] == "主勝"
    assert result["actual_result_probability"] == pytest.approx(
        prediction.home_win_probability
    )
    assert result["log_loss"] >= 0
    assert 0 <= result["ranked_probability_score"] <= 1
    assert result["lock_fingerprint_sha256"] == locked.fingerprint_sha256
    aggregate = aggregate_prediction_evaluations([result])
    assert aggregate["matches"] == 1
    assert aggregate["mean_log_loss"] == pytest.approx(result["log_loss"])


def test_prediction_lock_rejects_post_lock_data(calendar_context):
    prediction = _prediction(calendar_context)
    prediction.model_input["data_as_of"] = (
        calendar_context.local_datetime - timedelta(hours=1)
    ).isoformat()
    with pytest.raises(ValueError, match="不可晚於預測鎖定"):
        lock_prediction(
            "JARVIS-LEAK",
            calendar_context.local_datetime,
            calendar_context.local_datetime - timedelta(hours=8),
            prediction,
        )


def test_prediction_horizon_cutoffs_are_enforced(calendar_context):
    prediction = _prediction(calendar_context)
    with pytest.raises(ValueError, match="EARLY 預測鎖定時間晚於"):
        lock_prediction(
            "JARVIS-LATE-EARLY",
            calendar_context.local_datetime,
            calendar_context.local_datetime - timedelta(hours=5),
            prediction,
        )


def test_lock_fingerprint_covers_experiment_and_block_metadata(calendar_context):
    prediction = _prediction(calendar_context)
    locked_at = calendar_context.local_datetime - timedelta(hours=8)
    first = lock_prediction(
        "JARVIS-META", calendar_context.local_datetime, locked_at, prediction,
        competition="League", evaluation_block="W01",
    )
    second = lock_prediction(
        "JARVIS-META", calendar_context.local_datetime, locked_at, prediction,
        competition="League", evaluation_block="W02",
    )
    assert first.fingerprint_sha256 != second.fingerprint_sha256
    with pytest.raises(ValueError, match="experiment_id"):
        lock_prediction(
            "JARVIS-UNTOUCHED", calendar_context.local_datetime, locked_at, prediction,
            dataset_role="TEST_UNTOUCHED",
        )


def _evaluation_row(
    match_id: str,
    actual_result: str,
    probabilities: tuple[float, float, float],
    *,
    competition: str,
    block: str,
) -> dict[str, object]:
    labels = ("主勝", "和局", "客勝")
    predicted_result = labels[max(range(3), key=lambda index: probabilities[index])]
    observation = tuple(1.0 if label == actual_result else 0.0 for label in labels)
    actual_probability = probabilities[labels.index(actual_result)]
    return {
        "match_id": match_id,
        "competition": competition,
        "evaluation_block": block,
        "actual_result": actual_result,
        "predicted_result": predicted_result,
        "home_win_probability": probabilities[0],
        "draw_probability": probabilities[1],
        "away_win_probability": probabilities[2],
        "top1_result_correct": predicted_result == actual_result,
        "log_loss": -__import__("math").log(actual_probability),
        "brier_score": sum((probability - outcome) ** 2 for probability, outcome in zip(probabilities, observation)),
        "ranked_probability_score": 0.0,
        "exact_score_top1_hit": False,
        "exact_score_top3_hit": False,
    }


def test_complete_aggregate_metrics_and_paired_block_bootstrap():
    actuals = ("主勝", "和局", "客勝")
    champion = [
        _evaluation_row(
            f"M-{index}", actuals[index % 3],
            tuple(0.50 if position == index % 3 else 0.25 for position in range(3)),
            competition="League A",
            block=f"W{index // 3}",
        )
        for index in range(30)
    ]
    challenger = [
        _evaluation_row(
            f"M-{index}", actuals[index % 3],
            tuple(0.60 if position == index % 3 else 0.20 for position in range(3)),
            competition="League A",
            block=f"W{index // 3}",
        )
        for index in range(30)
    ]
    aggregate = aggregate_prediction_evaluations(challenger, total_matches=40)
    assert aggregate["macro_f1"] == pytest.approx(1.0)
    assert aggregate["draw_recall"] == pytest.approx(1.0)
    assert aggregate["coverage"] == pytest.approx(0.75)
    assert aggregate["ece_classwise"] >= 0

    comparison = compare_prediction_models(
        champion, challenger, bootstrap_samples=100, seed=7,
    )
    assert comparison["mean_delta"] < 0
    assert comparison["ci_upper"] < 0
    assert comparison["blocks"] == 10


def test_qimen_gate_never_auto_activates_and_requires_full_blind_sample():
    actuals = ("主勝", "和局", "客勝")
    champion: list[dict[str, object]] = []
    challenger: list[dict[str, object]] = []
    for index in range(30):
        actual = actuals[index % 3]
        champion.append(_evaluation_row(
            f"G-{index}", actual,
            tuple(0.50 if position == index % 3 else 0.25 for position in range(3)),
            competition="League A" if index % 2 else "League B",
            block=f"W{index // 3}",
        ))
        challenger.append(_evaluation_row(
            f"G-{index}", actual,
            tuple(0.60 if position == index % 3 else 0.20 for position in range(3)),
            competition="League A" if index % 2 else "League B",
            block=f"W{index // 3}",
        ))
    gate = qimen_activation_gate(champion, challenger, bootstrap_samples=100, seed=7)
    assert gate["status"] == "KEEP_SHADOW"
    assert gate["automatic_activation"] is False
    assert gate["checks"]["untouched_matches_at_least_5000"] is False


def test_qimen_gate_can_only_reach_human_review_after_all_controls_pass():
    actuals = ("主勝", "和局", "客勝")
    shared_hash = "a" * 64
    champion: list[dict[str, object]] = []
    challenger: list[dict[str, object]] = []
    for index in range(5000):
        metadata = {
            "dataset_role": "TEST_UNTOUCHED",
            "experiment_id": "EXP-LOCKED-001",
            "forecast_horizon": "EARLY",
            "data_snapshot_sha256": shared_hash,
            "football_feature_sha256": shared_hash,
            "qimen_feature_sha256": shared_hash,
            "git_commit": "f" * 40,
            "source_manifest_entries": 1,
            "calibration_status": "CALIBRATED_TEMPERATURE_V1",
        }
        champion_row = _evaluation_row(
            f"BLIND-{index}", actuals[index % 3],
            tuple(0.50 if position == index % 3 else 0.25 for position in range(3)),
            competition=f"League {index % 2}", block=f"W{index // 500}",
        )
        challenger_row = _evaluation_row(
            f"BLIND-{index}", actuals[index % 3],
            tuple(0.60 if position == index % 3 else 0.20 for position in range(3)),
            competition=f"League {index % 2}", block=f"W{index // 500}",
        )
        champion_row.update({
            **metadata,
            "lock_fingerprint_sha256": "b" * 64,
            "model_spec_sha256": "c" * 64,
        })
        challenger_row.update({
            **metadata,
            "lock_fingerprint_sha256": "d" * 64,
            "model_spec_sha256": "e" * 64,
        })
        champion.append(champion_row)
        challenger.append(challenger_row)

    gate = qimen_activation_gate(champion, challenger, bootstrap_samples=100, seed=11)
    assert gate["status"] == "ELIGIBLE_FOR_REVIEW"
    assert gate["automatic_activation"] is False
    assert all(gate["checks"].values())
