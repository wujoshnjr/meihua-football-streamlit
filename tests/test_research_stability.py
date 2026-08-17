from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from jarvis.research.experiment import (
    ModelForecast,
    PrematchExperimentRecord,
    SnapshotRef,
    evaluate_forecast,
)
from jarvis.research.stability import paired_block_bootstrap, rolling_block_stability


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
        experiment_id="stability-exp",
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


def _fixture():
    blocks = ("week-01", "week-01", "week-02", "week-02", "week-03", "week-03", "week-04", "week-04")
    records = tuple(_record(index, block) for index, block in enumerate(blocks))
    baseline = tuple(
        evaluate_forecast(record, _forecast(record, "M0_FOOTBALL", 0.45, 0.40))
        for record in records
    )
    challenger = tuple(
        evaluate_forecast(record, _forecast(record, "M1_QIMEN", 0.65, 0.60))
        for record in records
    )
    return records, baseline, challenger


def test_rolling_blocks_show_consistent_improvement():
    records, baseline, challenger = _fixture()
    report = rolling_block_stability(records, baseline, challenger, window_blocks=2)

    assert report["blocks"] == 4
    assert len(report["windows"]) == 3
    assert report["metric_stability"]["result_log_loss_delta"]["better_in_every_window"] is True
    assert report["metric_stability"]["exact_score_nll_delta"]["worst_window_delta"] < 0


def test_paired_block_bootstrap_is_deterministic_and_excludes_zero_for_uniform_gain():
    records, baseline, challenger = _fixture()
    first = paired_block_bootstrap(records, baseline, challenger, samples=400, seed=17)
    second = paired_block_bootstrap(records, baseline, challenger, samples=400, seed=17)

    assert first == second
    interval = first["intervals"]["result_log_loss_delta"]
    assert interval["upper"] < 0
    assert interval["interval_excludes_zero_in_favor_of_challenger"] is True
    assert interval["challenger_better_probability"] == 1.0


def test_stability_rejects_non_untouched_rows():
    records, baseline, challenger = _fixture()
    validation_record = _record(0, "week-01", role="VALIDATION")
    bad_records = (validation_record, *records[1:])

    with pytest.raises(ValueError, match="只允許 TEST_UNTOUCHED"):
        rolling_block_stability(bad_records, baseline, challenger, window_blocks=2)


def test_stability_rejects_reappearing_time_block():
    records, _, _ = _fixture()
    bad_blocks = ("week-01", "week-02", "week-01", "week-02", "week-03", "week-03", "week-04", "week-04")
    bad_records = tuple(
        PrematchExperimentRecord(**{**record.__dict__, "evaluation_block": block})
        for record, block in zip(records, bad_blocks)
    )
    baseline = tuple(
        evaluate_forecast(record, _forecast(record, "M0_FOOTBALL", 0.45, 0.40))
        for record in bad_records
    )
    challenger = tuple(
        evaluate_forecast(record, _forecast(record, "M1_QIMEN", 0.65, 0.60))
        for record in bad_records
    )

    with pytest.raises(ValueError, match="不可離開後再次出現"):
        paired_block_bootstrap(bad_records, baseline, challenger, samples=200)
