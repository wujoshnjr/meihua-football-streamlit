from dataclasses import replace
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from jarvis.research.experiment import (
    ModelForecast,
    PrematchExperimentRecord,
    SnapshotRef,
    evaluate_forecast,
)
from jarvis.research.promotion import PromotionPolicy, review_model_promotion


TZ = ZoneInfo("Asia/Taipei")


def _snapshot(cutoff: datetime, token: str) -> SnapshotRef:
    return SnapshotRef(
        source=f"fixture-{token}",
        schema_version="fixture-v1",
        available_at=cutoff - timedelta(minutes=1),
        payload_sha256=token * 64,
    )


def _record(index: int, block: str, *, role: str = "TEST_UNTOUCHED") -> PrematchExperimentRecord:
    event_at = datetime(2026, 1, 1, 20, tzinfo=TZ) + timedelta(days=index)
    cutoff = event_at - timedelta(hours=6)
    return PrematchExperimentRecord(
        match_id=f"m{index}",
        competition="Test League",
        event_at=event_at,
        cutoff=cutoff,
        venue_mode="TRUE_HOME",
        dataset_role=role,
        evaluation_block=block,
        experiment_id="promotion-exp",
        football_snapshot=_snapshot(cutoff, "a"),
        qimen_snapshot=_snapshot(cutoff, "b"),
        meihua_snapshot=_snapshot(cutoff, "c"),
        actual_home_goals=1,
        actual_away_goals=0,
    )


def _forecast(record: PrematchExperimentRecord, family: str, p_home: float, p_score: float) -> ModelForecast:
    p_draw = 0.25
    p_away = 1.0 - p_home - p_draw
    remainder = 1.0 - p_score
    return ModelForecast(
        match_id=record.match_id,
        model_family=family,
        model_version="fixture-v1",
        home_win_probability=p_home,
        draw_probability=p_draw,
        away_win_probability=p_away,
        expected_home_goals=1.4,
        expected_away_goals=0.8,
        score_grid=(
            (1, 0, p_score),
            (0, 0, remainder * 0.4),
            (1, 1, remainder * 0.4),
            (0, 1, remainder * 0.2),
        ),
    )


def _fixture(*, challenger_home: float = 0.65, challenger_score: float = 0.60):
    blocks = ("week-01", "week-01", "week-02", "week-02", "week-03", "week-03", "week-04", "week-04")
    records = tuple(_record(index, block) for index, block in enumerate(blocks))
    baseline = tuple(
        evaluate_forecast(record, _forecast(record, "M0_FOOTBALL", 0.45, 0.40))
        for record in records
    )
    challenger = tuple(
        evaluate_forecast(
            record,
            _forecast(record, "M1_QIMEN", challenger_home, challenger_score),
        )
        for record in records
    )
    return records, baseline, challenger


def _policy(**overrides) -> PromotionPolicy:
    values = {
        "policy_id": "fixture-policy-v1",
        "registered_at": datetime(2025, 12, 1, 12, tzinfo=TZ),
        "baseline_family": "M0_FOOTBALL",
        "challenger_family": "M1_QIMEN",
        "min_matches": 8,
        "min_blocks": 4,
        "min_competitions": 1,
        "min_log_loss_relative_improvement": 0.001,
        "max_classwise_ece_degradation": 1.0,
        "min_log_loss_better_window_fraction": 1.0,
        "window_blocks": 2,
        "bootstrap_samples": 400,
        "confidence": 0.95,
        "seed": 17,
    }
    values.update(overrides)
    return PromotionPolicy(**values)


def test_uniform_gain_becomes_eligible_for_human_review_only():
    records, baseline, challenger = _fixture()
    policy = _policy()

    report = review_model_promotion(records, baseline, challenger, policy)

    assert report["status"] == "ELIGIBLE_FOR_HUMAN_REVIEW"
    assert report["automatic_promotion"] is False
    assert report["failed_checks"] == ()
    assert report["policy_artifact_source"].startswith("promotion-policy:")
    assert len(report["report_sha256"]) == 64
    assert report["bootstrap"]["intervals"]["result_log_loss_delta"]["upper"] < 0
    assert report["rolling_stability"]["metric_stability"]["result_log_loss_delta"]["better_window_fraction"] == 1.0


def test_worse_challenger_stays_challenger():
    records, baseline, challenger = _fixture(challenger_home=0.35, challenger_score=0.20)

    report = review_model_promotion(records, baseline, challenger, _policy())

    assert report["status"] == "KEEP_CHALLENGER"
    assert report["automatic_promotion"] is False
    assert "log_loss_relative_improvement" in report["failed_checks"]
    assert "log_loss_ci_excludes_zero" in report["failed_checks"]


def test_policy_must_be_registered_before_first_untouched_cutoff():
    records, baseline, challenger = _fixture()
    too_late = replace(_policy(), registered_at=records[0].cutoff + timedelta(minutes=1))

    with pytest.raises(ValueError, match="第一個 TEST_UNTOUCHED cutoff 前"):
        review_model_promotion(records, baseline, challenger, too_late)


def test_promotion_review_rejects_non_untouched_records():
    records, baseline, challenger = _fixture()
    bad_records = (replace(records[0], dataset_role="VALIDATION"), *records[1:])

    with pytest.raises(ValueError, match="只允許 TEST_UNTOUCHED"):
        review_model_promotion(bad_records, baseline, challenger, _policy())


def test_policy_family_binding_cannot_be_changed_after_test():
    records, baseline, challenger = _fixture()
    wrong_family = replace(_policy(), challenger_family="M2_MEIHUA")

    with pytest.raises(ValueError, match="challenger family"):
        review_model_promotion(records, baseline, challenger, wrong_family)
