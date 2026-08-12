"""Leakage-resistant evaluation for the separate football prediction layer.

This module deliberately does not import the casting engine.  Forecasts are
locked before results are known, results live in another file, and evaluation
is chronological so later outcomes cannot improve earlier benchmark forecasts.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from itertools import groupby
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from version import FORECAST_PROTOCOL_VERSION


OUTCOMES = ("body", "draw", "use")
SAMPLE_CLASSES = ("CLEAN_BLIND", "EXPOSED_BLIND", "POSTMATCH_ANALYSIS")
SOURCE_GRADES = ("A", "B", "C")
PROBABILITY_TOLERANCE = 1e-6

FORECAST_COLUMNS = (
    "forecast_id",
    "casting_id",
    "method_version",
    "sample_class",
    "event_at",
    "freeze_at",
    "locked_at",
    "body_name",
    "use_name",
    "p_body",
    "p_draw",
    "p_use",
    "top1_score",
    "goal_band",
    "btts",
    "signal_key",
    "source_grade",
    "source_urls",
    "forecast_sha256",
)

RESULT_COLUMNS = (
    "forecast_id",
    "result_recorded_at",
    "body_goals",
    "use_goals",
    "result_source_url",
    "result_sha256",
)


def parse_aware_iso(value: str, field_name: str) -> datetime:
    normalized = str(value or "").strip().replace("Z", "+00:00")
    if not normalized:
        raise ValueError(f"{field_name} 不可為空。")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError(f"{field_name} 必須是含時區的 ISO 8601 時間。") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field_name} 必須包含 UTC 位移。")
    return parsed.replace(microsecond=0)


def freeze_at_for(event_at: datetime) -> datetime:
    if event_at.tzinfo is None or event_at.utcoffset() is None:
        raise ValueError("event_at 必須包含 UTC 位移。")
    return event_at.replace(microsecond=0) - timedelta(hours=6)


def _canonical_sha256(payload: Mapping[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _required(row: Mapping[str, Any], name: str) -> str:
    value = str(row.get(name, "") or "").strip()
    if not value:
        raise ValueError(f"{name} 不可為空。")
    return value


def _probability(row: Mapping[str, Any], name: str) -> float:
    raw = _required(row, name)
    try:
        value = float(raw)
    except ValueError as exc:
        raise ValueError(f"{name} 必須是數字。") from exc
    if not 0 < value < 1:
        raise ValueError(f"{name} 必須大於 0 且小於 1，避免 log loss 無限大。")
    return value


def _non_negative_integer(row: Mapping[str, Any], name: str) -> int:
    raw = _required(row, name)
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} 必須是非負整數。") from exc
    if value < 0:
        raise ValueError(f"{name} 必須是非負整數。")
    return value


@dataclass(frozen=True, slots=True)
class ForecastRecord:
    forecast_id: str
    casting_id: str
    method_version: str
    sample_class: str
    event_at: datetime
    freeze_at: datetime
    locked_at: datetime
    body_name: str
    use_name: str
    p_body: float
    p_draw: float
    p_use: float
    top1_score: str = ""
    goal_band: str = ""
    btts: str = ""
    signal_key: str = ""
    source_grade: str = ""
    source_urls: str = ""
    forecast_sha256: str = ""

    @classmethod
    def from_row(
        cls,
        row: Mapping[str, Any],
        *,
        verify_fingerprint: bool = True,
    ) -> "ForecastRecord":
        event_at = parse_aware_iso(_required(row, "event_at"), "event_at")
        freeze_raw = str(row.get("freeze_at", "") or "").strip()
        freeze_at = (
            parse_aware_iso(freeze_raw, "freeze_at") if freeze_raw else freeze_at_for(event_at)
        )
        record = cls(
            forecast_id=_required(row, "forecast_id"),
            casting_id=_required(row, "casting_id"),
            method_version=_required(row, "method_version"),
            sample_class=_required(row, "sample_class"),
            event_at=event_at,
            freeze_at=freeze_at,
            locked_at=parse_aware_iso(_required(row, "locked_at"), "locked_at"),
            body_name=_required(row, "body_name"),
            use_name=_required(row, "use_name"),
            p_body=_probability(row, "p_body"),
            p_draw=_probability(row, "p_draw"),
            p_use=_probability(row, "p_use"),
            top1_score=str(row.get("top1_score", "") or "").strip(),
            goal_band=str(row.get("goal_band", "") or "").strip(),
            btts=str(row.get("btts", "") or "").strip().upper(),
            signal_key=str(row.get("signal_key", "") or "").strip(),
            source_grade=str(row.get("source_grade", "") or "").strip().upper(),
            source_urls=str(row.get("source_urls", "") or "").strip(),
            forecast_sha256=str(row.get("forecast_sha256", "") or "").strip().lower(),
        )
        record.validate(verify_fingerprint=verify_fingerprint)
        return record

    @property
    def probabilities(self) -> dict[str, float]:
        return {"body": self.p_body, "draw": self.p_draw, "use": self.p_use}

    def canonical_payload(self) -> dict[str, Any]:
        return {
            "forecast_protocol_version": FORECAST_PROTOCOL_VERSION,
            "forecast_id": self.forecast_id,
            "casting_id": self.casting_id,
            "method_version": self.method_version,
            "sample_class": self.sample_class,
            "event_at": self.event_at.isoformat(timespec="seconds"),
            "freeze_at": self.freeze_at.isoformat(timespec="seconds"),
            "locked_at": self.locked_at.isoformat(timespec="seconds"),
            "body_name": self.body_name,
            "use_name": self.use_name,
            "p_body": self.p_body,
            "p_draw": self.p_draw,
            "p_use": self.p_use,
            "top1_score": self.top1_score,
            "goal_band": self.goal_band,
            "btts": self.btts,
            "signal_key": self.signal_key,
            "source_grade": self.source_grade,
            "source_urls": self.source_urls,
        }

    @property
    def calculated_fingerprint(self) -> str:
        return _canonical_sha256(self.canonical_payload())

    def validate(self, *, verify_fingerprint: bool = True) -> None:
        if self.sample_class not in SAMPLE_CLASSES:
            raise ValueError(f"sample_class 必須是：{', '.join(SAMPLE_CLASSES)}。")
        if self.source_grade not in SOURCE_GRADES:
            raise ValueError("source_grade 必須是 A、B 或 C。")
        if self.source_grade in {"A", "B"} and not self.source_urls:
            raise ValueError("A／B 級資料必須保存 source_urls。")
        expected_freeze = freeze_at_for(self.event_at)
        if abs((self.freeze_at - expected_freeze).total_seconds()) > 1:
            raise ValueError("freeze_at 必須固定等於 event_at − 6 小時。")
        if self.sample_class == "CLEAN_BLIND" and self.locked_at > self.freeze_at:
            raise ValueError("CLEAN_BLIND 必須在 freeze_at 前完成鎖定。")
        probability_sum = sum(self.probabilities.values())
        if abs(probability_sum - 1.0) > PROBABILITY_TOLERANCE:
            raise ValueError(f"p_body、p_draw、p_use 合計必須為 1；目前為 {probability_sum:.8f}。")
        if self.top1_score:
            _parse_score(self.top1_score, "top1_score")
        if self.goal_band and self.goal_band not in {"0-1", "2-3", "4+"}:
            raise ValueError("goal_band 必須是 0-1、2-3 或 4+。")
        if self.btts and self.btts not in {"YES", "NO"}:
            raise ValueError("btts 必須是 YES 或 NO。")
        if verify_fingerprint:
            if not self.forecast_sha256:
                raise ValueError("forecast_sha256 不可為空；請先執行 lock。")
            if self.forecast_sha256 != self.calculated_fingerprint:
                raise ValueError(f"forecast_id={self.forecast_id} 的鎖定指紋不符。")

    def to_row(self) -> dict[str, str]:
        values = self.canonical_payload()
        values.pop("forecast_protocol_version")
        values["p_body"] = format(self.p_body, ".12g")
        values["p_draw"] = format(self.p_draw, ".12g")
        values["p_use"] = format(self.p_use, ".12g")
        values["forecast_sha256"] = self.calculated_fingerprint
        return {column: str(values.get(column, "")) for column in FORECAST_COLUMNS}


@dataclass(frozen=True, slots=True)
class ResultRecord:
    forecast_id: str
    result_recorded_at: datetime
    body_goals: int
    use_goals: int
    result_source_url: str
    result_sha256: str = ""

    @classmethod
    def from_row(
        cls,
        row: Mapping[str, Any],
        *,
        verify_fingerprint: bool = True,
    ) -> "ResultRecord":
        record = cls(
            forecast_id=_required(row, "forecast_id"),
            result_recorded_at=parse_aware_iso(
                _required(row, "result_recorded_at"), "result_recorded_at"
            ),
            body_goals=_non_negative_integer(row, "body_goals"),
            use_goals=_non_negative_integer(row, "use_goals"),
            result_source_url=_required(row, "result_source_url"),
            result_sha256=str(row.get("result_sha256", "") or "").strip().lower(),
        )
        record.validate(verify_fingerprint=verify_fingerprint)
        return record

    def canonical_payload(self) -> dict[str, Any]:
        return {
            "forecast_id": self.forecast_id,
            "result_recorded_at": self.result_recorded_at.isoformat(timespec="seconds"),
            "body_goals": self.body_goals,
            "use_goals": self.use_goals,
            "result_source_url": self.result_source_url,
        }

    @property
    def calculated_fingerprint(self) -> str:
        return _canonical_sha256(self.canonical_payload())

    def validate(self, *, verify_fingerprint: bool = True) -> None:
        if verify_fingerprint:
            if not self.result_sha256:
                raise ValueError("result_sha256 不可為空；請先執行 lock-results。")
            if self.result_sha256 != self.calculated_fingerprint:
                raise ValueError(f"forecast_id={self.forecast_id} 的賽果指紋不符。")

    def to_row(self) -> dict[str, str]:
        values = self.canonical_payload()
        values["result_sha256"] = self.calculated_fingerprint
        return {column: str(values.get(column, "")) for column in RESULT_COLUMNS}


@dataclass(frozen=True, slots=True)
class EvaluatedForecast:
    forecast: ForecastRecord
    result: ResultRecord
    outcome: str
    baseline_probabilities: Mapping[str, float]


def _parse_score(value: str, field_name: str) -> tuple[int, int]:
    parts = value.strip().split("-")
    if len(parts) != 2:
        raise ValueError(f"{field_name} 必須使用 body-use 格式，例如 2-1。")
    try:
        goals = tuple(int(part) for part in parts)
    except ValueError as exc:
        raise ValueError(f"{field_name} 必須使用非負整數，例如 2-1。") from exc
    if any(goal < 0 for goal in goals):
        raise ValueError(f"{field_name} 必須使用非負整數。")
    return goals[0], goals[1]


def observed_outcome(result: ResultRecord) -> str:
    if result.body_goals > result.use_goals:
        return "body"
    if result.body_goals < result.use_goals:
        return "use"
    return "draw"


def brier_score(probabilities: Mapping[str, float], outcome: str) -> float:
    """Unnormalised multiclass Brier score, range 0..2 for 1X2."""

    return sum((float(probabilities[name]) - float(name == outcome)) ** 2 for name in OUTCOMES)


def log_loss(probabilities: Mapping[str, float], outcome: str) -> float:
    return -math.log(float(probabilities[outcome]))


def _top_pick(probabilities: Mapping[str, float]) -> str:
    # The fixed order makes exact ties reproducible and auditable.
    return max(OUTCOMES, key=lambda name: (float(probabilities[name]), -OUTCOMES.index(name)))


def _goal_band(result: ResultRecord) -> str:
    total = result.body_goals + result.use_goals
    if total <= 1:
        return "0-1"
    if total <= 3:
        return "2-3"
    return "4+"


def _btts(result: ResultRecord) -> str:
    return "YES" if result.body_goals > 0 and result.use_goals > 0 else "NO"


def _mean(values: Sequence[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _accuracy(values: Sequence[bool]) -> float | None:
    return sum(values) / len(values) if values else None


def _calibration(records: Sequence[EvaluatedForecast], bins: int = 5) -> dict[str, Any]:
    details: dict[str, list[dict[str, Any]]] = {}
    absolute_error_sum = 0.0
    observation_count = 0
    for outcome_name in OUTCOMES:
        outcome_bins: list[dict[str, Any]] = []
        for index in range(bins):
            low = index / bins
            high = (index + 1) / bins
            members = [
                item
                for item in records
                if low <= item.forecast.probabilities[outcome_name]
                and (
                    item.forecast.probabilities[outcome_name] < high
                    or (index == bins - 1 and item.forecast.probabilities[outcome_name] <= high)
                )
            ]
            if not members:
                continue
            predicted = _mean(
                [item.forecast.probabilities[outcome_name] for item in members]
            )
            observed = _mean([float(item.outcome == outcome_name) for item in members])
            assert predicted is not None and observed is not None
            absolute_error_sum += len(members) * abs(predicted - observed)
            observation_count += len(members)
            outcome_bins.append(
                {
                    "range": [low, high],
                    "n": len(members),
                    "mean_predicted": predicted,
                    "observed_frequency": observed,
                    "absolute_gap": abs(predicted - observed),
                }
            )
        details[outcome_name] = outcome_bins
    return {
        "classwise_ece": absolute_error_sum / observation_count if observation_count else None,
        "bins": details,
        "warning": "少量樣本的校準分箱波動很大，僅作診斷。" if len(records) < 100 else "",
    }


def _prequential_baselines(
    pairs: Sequence[tuple[ForecastRecord, ResultRecord]],
) -> dict[str, dict[str, float]]:
    """Expanding 1X2 base rates with Laplace smoothing and no future leakage."""

    counts = {name: 0 for name in OUTCOMES}
    total = 0
    baselines: dict[str, dict[str, float]] = {}
    ordered = sorted(pairs, key=lambda item: (item[0].event_at, item[0].forecast_id))
    for _, simultaneous in groupby(ordered, key=lambda item: item[0].event_at):
        group = list(simultaneous)
        probabilities = {name: (counts[name] + 1) / (total + 3) for name in OUTCOMES}
        for forecast, _ in group:
            baselines[forecast.forecast_id] = dict(probabilities)
        # Outcomes at the same event time are revealed only after every forecast
        # in that time group has received its pre-event baseline.
        for _, result in group:
            counts[observed_outcome(result)] += 1
            total += 1
    return baselines


def _metric_block(records: Sequence[EvaluatedForecast]) -> dict[str, Any]:
    model_brier = [
        brier_score(item.forecast.probabilities, item.outcome) for item in records
    ]
    model_log = [log_loss(item.forecast.probabilities, item.outcome) for item in records]
    baseline_brier = [
        brier_score(item.baseline_probabilities, item.outcome) for item in records
    ]
    baseline_log = [log_loss(item.baseline_probabilities, item.outcome) for item in records]
    exact_items = [item for item in records if item.forecast.top1_score]
    band_items = [item for item in records if item.forecast.goal_band]
    btts_items = [item for item in records if item.forecast.btts]
    model_brier_mean = _mean(model_brier)
    model_log_mean = _mean(model_log)
    baseline_brier_mean = _mean(baseline_brier)
    baseline_log_mean = _mean(baseline_log)
    return {
        "n": len(records),
        "top1_accuracy": _accuracy(
            [_top_pick(item.forecast.probabilities) == item.outcome for item in records]
        ),
        "mean_brier_1x2": model_brier_mean,
        "mean_log_loss_1x2": model_log_mean,
        "mean_prequential_baseline_brier": baseline_brier_mean,
        "mean_prequential_baseline_log_loss": baseline_log_mean,
        "brier_skill_vs_baseline": (
            1 - model_brier_mean / baseline_brier_mean
            if model_brier_mean is not None and baseline_brier_mean
            else None
        ),
        "log_loss_skill_vs_baseline": (
            1 - model_log_mean / baseline_log_mean
            if model_log_mean is not None and baseline_log_mean
            else None
        ),
        "exact_score_top1": {
            "n": len(exact_items),
            "accuracy": _accuracy(
                [
                    _parse_score(item.forecast.top1_score, "top1_score")
                    == (item.result.body_goals, item.result.use_goals)
                    for item in exact_items
                ]
            ),
        },
        "goal_band": {
            "n": len(band_items),
            "accuracy": _accuracy(
                [item.forecast.goal_band == _goal_band(item.result) for item in band_items]
            ),
        },
        "btts": {
            "n": len(btts_items),
            "accuracy": _accuracy(
                [item.forecast.btts == _btts(item.result) for item in btts_items]
            ),
        },
        "calibration": _calibration(records),
    }


def _promotion_gate(
    metrics: Mapping[str, Any], minimum_samples: int, sample_class: str
) -> dict[str, Any]:
    n = int(metrics["n"])
    if sample_class != "CLEAN_BLIND":
        status = "NOT_ELIGIBLE"
        reason = "只有 CLEAN_BLIND 可以晉升正式方法版本。"
    elif n < minimum_samples:
        status = "INSUFFICIENT_DATA"
        reason = f"需至少 {minimum_samples} 場 CLEAN_BLIND，目前 {n} 場。"
    elif (
        float(metrics["brier_skill_vs_baseline"] or 0) > 0
        and float(metrics["log_loss_skill_vs_baseline"] or 0) > 0
    ):
        status = "PASS"
        reason = "Brier 與 log loss 均優於只使用過去賽果的基準線。"
    else:
        status = "FAIL"
        reason = "尚未同時在 Brier 與 log loss 上優於基準線。"
    return {"status": status, "minimum_samples": minimum_samples, "reason": reason}


def evaluate_records(
    forecasts: Sequence[ForecastRecord],
    results: Sequence[ResultRecord],
    *,
    sample_class: str = "CLEAN_BLIND",
    minimum_samples: int = 100,
) -> dict[str, Any]:
    if sample_class not in SAMPLE_CLASSES:
        raise ValueError(f"sample_class 必須是：{', '.join(SAMPLE_CLASSES)}。")
    forecast_ids = [item.forecast_id for item in forecasts]
    result_ids = [item.forecast_id for item in results]
    if len(forecast_ids) != len(set(forecast_ids)):
        raise ValueError("forecasts 存在重複 forecast_id。")
    if len(result_ids) != len(set(result_ids)):
        raise ValueError("results 存在重複 forecast_id。")
    result_by_id = {item.forecast_id: item for item in results}
    pairs = [
        (forecast, result_by_id[forecast.forecast_id])
        for forecast in forecasts
        if forecast.sample_class == sample_class and forecast.forecast_id in result_by_id
    ]
    for forecast, result in pairs:
        if result.result_recorded_at < forecast.event_at:
            raise ValueError(
                f"forecast_id={forecast.forecast_id} 的 result_recorded_at 早於 event_at。"
            )
    baselines = _prequential_baselines(pairs)
    evaluated = [
        EvaluatedForecast(
            forecast=forecast,
            result=result,
            outcome=observed_outcome(result),
            baseline_probabilities=baselines[forecast.forecast_id],
        )
        for forecast, result in sorted(
            pairs, key=lambda item: (item[0].event_at, item[0].forecast_id)
        )
    ]
    overall = _metric_block(evaluated)
    methods: dict[str, Any] = {}
    for method_version in sorted({item.forecast.method_version for item in evaluated}):
        method_records = [
            item for item in evaluated if item.forecast.method_version == method_version
        ]
        method_metrics = _metric_block(method_records)
        method_metrics["promotion_gate"] = _promotion_gate(
            method_metrics, minimum_samples, sample_class
        )
        methods[method_version] = method_metrics
    overall["promotion_gate"] = _promotion_gate(
        overall, minimum_samples, sample_class
    )
    return {
        "forecast_protocol_version": FORECAST_PROTOCOL_VERSION,
        "eligibility": {
            "sample_class": sample_class,
            "joined_records": len(evaluated),
            "unmatched_forecasts": sum(
                1
                for item in forecasts
                if item.sample_class == sample_class and item.forecast_id not in result_by_id
            ),
            "rule": "主要報告只使用已鎖定預測與獨立賽果表的交集。",
        },
        "overall": overall,
        "by_method_version": methods,
        "metric_definitions": {
            "brier_1x2": "sum((p_k-o_k)^2)，範圍 0..2，越低越好。",
            "log_loss_1x2": "-ln(p_observed)，越低越好。",
            "prequential_baseline": "只用事件時間嚴格早於本場的賽果頻率，Laplace +1 平滑。",
            "skill": "1 - model_loss / baseline_loss；大於 0 才優於基準。",
        },
    }


def _read_rows(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _csv_text(rows: Iterable[Mapping[str, Any]], columns: Sequence[str]) -> str:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=columns, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def _write_csv(path: str | Path, rows: Iterable[Mapping[str, Any]], columns: Sequence[str]) -> None:
    Path(path).write_text("\ufeff" + _csv_text(rows, columns), encoding="utf-8")


def lock_forecast_csv(input_path: str | Path, output_path: str | Path) -> list[ForecastRecord]:
    records = [
        ForecastRecord.from_row(row, verify_fingerprint=False) for row in _read_rows(input_path)
    ]
    if len({item.forecast_id for item in records}) != len(records):
        raise ValueError("forecasts 存在重複 forecast_id。")
    _write_csv(output_path, (item.to_row() for item in records), FORECAST_COLUMNS)
    return records


def lock_result_csv(input_path: str | Path, output_path: str | Path) -> list[ResultRecord]:
    records = [
        ResultRecord.from_row(row, verify_fingerprint=False) for row in _read_rows(input_path)
    ]
    if len({item.forecast_id for item in records}) != len(records):
        raise ValueError("results 存在重複 forecast_id。")
    _write_csv(output_path, (item.to_row() for item in records), RESULT_COLUMNS)
    return records


def load_forecasts(path: str | Path) -> list[ForecastRecord]:
    return [ForecastRecord.from_row(row) for row in _read_rows(path)]


def load_results(path: str | Path) -> list[ResultRecord]:
    return [ResultRecord.from_row(row) for row in _read_rows(path)]


__all__ = [
    "FORECAST_COLUMNS",
    "FORECAST_PROTOCOL_VERSION",
    "OUTCOMES",
    "RESULT_COLUMNS",
    "SAMPLE_CLASSES",
    "ForecastRecord",
    "ResultRecord",
    "brier_score",
    "evaluate_records",
    "freeze_at_for",
    "load_forecasts",
    "load_results",
    "lock_forecast_csv",
    "lock_result_csv",
    "log_loss",
    "observed_outcome",
    "parse_aware_iso",
]
