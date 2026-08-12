from __future__ import annotations

import csv
import tempfile
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

from forecast_evaluation import (
    FORECAST_COLUMNS,
    RESULT_COLUMNS,
    ForecastRecord,
    ResultRecord,
    evaluate_records,
    freeze_at_for,
    load_forecasts,
    load_results,
    lock_forecast_csv,
    lock_result_csv,
)


UTC = timezone.utc


def _forecast(
    number: int,
    *,
    probabilities: tuple[float, float, float],
    sample_class: str = "CLEAN_BLIND",
) -> ForecastRecord:
    event_at = datetime(2026, 1, number, 20, 0, tzinfo=UTC)
    return ForecastRecord(
        forecast_id=f"F-{number}",
        casting_id=f"CAST-{number}",
        method_version="interpretation-v1",
        sample_class=sample_class,
        event_at=event_at,
        freeze_at=freeze_at_for(event_at),
        locked_at=event_at - timedelta(hours=7),
        body_name="甲",
        use_name="乙",
        p_body=probabilities[0],
        p_draw=probabilities[1],
        p_use=probabilities[2],
        top1_score="1-0",
        goal_band="0-1",
        btts="NO",
        signal_key="乾為天|初九|天風姤",
        source_grade="A",
        source_urls="https://example.test/prematch",
    )


def _result(number: int, body_goals: int, use_goals: int) -> ResultRecord:
    return ResultRecord(
        forecast_id=f"F-{number}",
        result_recorded_at=datetime(2026, 1, number, 23, 0, tzinfo=UTC),
        body_goals=body_goals,
        use_goals=use_goals,
        result_source_url="https://example.test/result",
    )


class ForecastEvaluationTests(unittest.TestCase):
    def test_clean_blind_must_be_locked_by_freeze_at(self) -> None:
        record = _forecast(1, probabilities=(0.6, 0.25, 0.15))
        late = ForecastRecord(
            forecast_id=record.forecast_id,
            casting_id=record.casting_id,
            method_version=record.method_version,
            sample_class=record.sample_class,
            event_at=record.event_at,
            freeze_at=record.freeze_at,
            locked_at=record.freeze_at + timedelta(seconds=1),
            body_name=record.body_name,
            use_name=record.use_name,
            p_body=record.p_body,
            p_draw=record.p_draw,
            p_use=record.p_use,
            source_grade="A",
            source_urls=record.source_urls,
        )
        with self.assertRaisesRegex(ValueError, "CLEAN_BLIND"):
            late.validate(verify_fingerprint=False)

    def test_forecast_and_result_fingerprints_detect_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            draft = root / "forecast_draft.csv"
            locked = root / "forecast_locked.csv"
            result_draft = root / "result_draft.csv"
            result_locked = root / "result_locked.csv"
            self._write_rows(draft, [_forecast(1, probabilities=(0.6, 0.25, 0.15)).to_row()], FORECAST_COLUMNS)
            self._write_rows(result_draft, [_result(1, 1, 0).to_row()], RESULT_COLUMNS)
            lock_forecast_csv(draft, locked)
            lock_result_csv(result_draft, result_locked)
            self.assertEqual(len(load_forecasts(locked)), 1)
            self.assertEqual(len(load_results(result_locked)), 1)

            text = locked.read_text(encoding="utf-8-sig").replace("0.6", "0.5", 1)
            locked.write_text(text, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "合計必須為 1|指紋不符"):
                load_forecasts(locked)

    def test_primary_report_is_probabilistic_chronological_and_clean_only(self) -> None:
        forecasts = [
            _forecast(1, probabilities=(0.8, 0.1, 0.1)),
            _forecast(2, probabilities=(0.1, 0.8, 0.1)),
            _forecast(3, probabilities=(0.1, 0.1, 0.8)),
            _forecast(
                4,
                probabilities=(0.8, 0.1, 0.1),
                sample_class="POSTMATCH_ANALYSIS",
            ),
        ]
        results = [_result(1, 1, 0), _result(2, 1, 1), _result(3, 0, 1), _result(4, 1, 0)]
        report = evaluate_records(forecasts, results, minimum_samples=3)

        self.assertEqual(report["overall"]["n"], 3)
        self.assertEqual(report["overall"]["top1_accuracy"], 1.0)
        self.assertLess(report["overall"]["mean_log_loss_1x2"], report["overall"]["mean_prequential_baseline_log_loss"])
        self.assertGreater(report["overall"]["brier_skill_vs_baseline"], 0)
        self.assertEqual(report["overall"]["promotion_gate"]["status"], "PASS")
        self.assertEqual(report["by_method_version"]["interpretation-v1"]["n"], 3)

    def test_simultaneous_events_cannot_leak_results_into_each_others_baseline(self) -> None:
        event_at = datetime(2026, 2, 1, 20, 0, tzinfo=UTC)
        forecasts = [
            replace(
                _forecast(1, probabilities=(0.8, 0.1, 0.1)),
                event_at=event_at,
                freeze_at=freeze_at_for(event_at),
                locked_at=event_at - timedelta(hours=7),
            ),
            replace(
                _forecast(2, probabilities=(0.1, 0.8, 0.1)),
                event_at=event_at,
                freeze_at=freeze_at_for(event_at),
                locked_at=event_at - timedelta(hours=7),
            ),
        ]
        results = [
            replace(_result(1, 1, 0), result_recorded_at=event_at + timedelta(hours=3)),
            replace(_result(2, 1, 1), result_recorded_at=event_at + timedelta(hours=3)),
        ]
        report = evaluate_records(forecasts, results)

        self.assertAlmostEqual(
            report["overall"]["mean_prequential_baseline_log_loss"],
            1.0986122886681098,
        )
        self.assertAlmostEqual(
            report["overall"]["mean_prequential_baseline_brier"],
            2 / 3,
        )

    @staticmethod
    def _write_rows(path: Path, rows: list[dict[str, str]], columns: tuple[str, ...]) -> None:
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)


if __name__ == "__main__":
    unittest.main()
