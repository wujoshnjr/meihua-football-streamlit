from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from jarvis.research.experiment import (
    ModelForecast,
    PrematchExperimentRecord,
    SnapshotRef,
    aggregate_evaluations,
    evaluate_forecast,
    paired_model_comparison,
    validate_chronological_dataset,
)


TZ = ZoneInfo("Asia/Taipei")


def _snapshot(cutoff: datetime, suffix: str) -> SnapshotRef:
    return SnapshotRef(
        source=f"fixture-{suffix}",
        schema_version=f"schema-{suffix}",
        available_at=cutoff - timedelta(minutes=1),
        payload_sha256=(suffix[0] * 64),
    )


def _record(index: int, role: str) -> PrematchExperimentRecord:
    event_at = datetime(2025, 1, 1, 20, tzinfo=TZ) + timedelta(days=index)
    cutoff = event_at - timedelta(hours=6)
    return PrematchExperimentRecord(
        match_id=f"m{index}",
        competition="Test League",
        event_at=event_at,
        cutoff=cutoff,
        venue_mode="TRUE_HOME",
        dataset_role=role,
        evaluation_block=f"block-{role.lower()}",
        experiment_id="exp-001",
        football_snapshot=_snapshot(cutoff, "a"),
        qimen_snapshot=_snapshot(cutoff, "b"),
        meihua_snapshot=_snapshot(cutoff, "c"),
        actual_home_goals=1,
        actual_away_goals=0,
    )


def _forecast(match_id: str, family: str, p_home: float) -> ModelForecast:
    p_draw = 0.25
    p_away = 1.0 - p_home - p_draw
    return ModelForecast(
        match_id=match_id,
        model_family=family,
        model_version="test-v1",
        home_win_probability=p_home,
        draw_probability=p_draw,
        away_win_probability=p_away,
        expected_home_goals=1.4,
        expected_away_goals=0.8,
        score_grid=((1, 0, 0.5), (0, 0, 0.2), (1, 1, 0.2), (0, 1, 0.1)),
    )


def test_record_rejects_post_cutoff_snapshot():
    record = _record(0, "TRAIN")
    late = SnapshotRef(
        source="late",
        schema_version="late-v1",
        available_at=record.cutoff + timedelta(seconds=1),
        payload_sha256="d" * 64,
    )
    record = PrematchExperimentRecord(**{**record.__dict__, "football_snapshot": late})
    assert any("leakage" in error for error in record.validate())


def test_chronological_roles_are_enforced():
    rows = (
        _record(0, "TRAIN"),
        _record(1, "VALIDATION"),
        _record(2, "CALIBRATION"),
        _record(3, "TEST_UNTOUCHED"),
    )
    assert validate_chronological_dataset(rows) == rows
    bad = (rows[0], _record(1, "TEST_UNTOUCHED"), _record(2, "CALIBRATION"), rows[3])
    with pytest.raises(ValueError, match="TRAIN → VALIDATION → CALIBRATION → TEST_UNTOUCHED"):
        validate_chronological_dataset(bad)


def test_evaluation_and_paired_comparison_reward_better_probability():
    record = _record(0, "TRAIN")
    baseline = evaluate_forecast(record, _forecast(record.match_id, "M0_FOOTBALL", 0.45))
    challenger = evaluate_forecast(record, _forecast(record.match_id, "M1_QIMEN", 0.65))
    assert challenger.result_log_loss < baseline.result_log_loss
    comparison = paired_model_comparison([baseline], [challenger])
    assert comparison["result_log_loss_delta"] < 0
    assert comparison["log_loss_better_match_fraction"] == 1.0


def test_aggregate_reports_classwise_calibration():
    rows = []
    for index, probability in enumerate((0.45, 0.55, 0.65, 0.75)):
        record = _record(index, "TRAIN")
        rows.append(evaluate_forecast(record, _forecast(record.match_id, "M0_FOOTBALL", probability)))
    summary = aggregate_evaluations(rows, calibration_bins=4)
    assert summary["matches"] == 4
    assert set(summary["classwise_ece"]) == {"HOME", "DRAW", "AWAY"}
    assert summary["mean_result_log_loss"] > 0


def test_paired_comparison_rejects_unmatched_games():
    first = evaluate_forecast(_record(0, "TRAIN"), _forecast("m0", "M0_FOOTBALL", 0.5))
    second = evaluate_forecast(_record(1, "TRAIN"), _forecast("m1", "M1_QIMEN", 0.6))
    with pytest.raises(ValueError, match="完全相同的 match_id"):
        paired_model_comparison([first], [second])
