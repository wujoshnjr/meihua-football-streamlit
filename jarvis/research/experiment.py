from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from math import isfinite, log
from typing import Any, Iterable, Literal

from jarvis.provenance import sha256_payload


EXPERIMENT_SCHEMA_VERSION = "jarvis-multisignal-experiment-v0.1.0"
DatasetRole = Literal["TRAIN", "VALIDATION", "CALIBRATION", "TEST_UNTOUCHED"]
ModelFamily = Literal["M0_FOOTBALL", "M1_QIMEN", "M2_MEIHUA", "M3_QIMEN_MEIHUA"]
VenueMode = Literal["TRUE_HOME", "NEUTRAL"]

VALID_DATASET_ROLES: tuple[DatasetRole, ...] = (
    "TRAIN",
    "VALIDATION",
    "CALIBRATION",
    "TEST_UNTOUCHED",
)
VALID_MODEL_FAMILIES: tuple[ModelFamily, ...] = (
    "M0_FOOTBALL",
    "M1_QIMEN",
    "M2_MEIHUA",
    "M3_QIMEN_MEIHUA",
)


def _valid_sha256(value: str) -> bool:
    return len(value) == 64 and all(character in "0123456789abcdef" for character in value)


@dataclass(frozen=True)
class SnapshotRef:
    """Immutable reference to information that was available before a cutoff."""

    source: str
    schema_version: str
    available_at: datetime
    payload_sha256: str

    def validate(self, label: str) -> list[str]:
        errors: list[str] = []
        if not self.source.strip():
            errors.append(f"{label} source 不可空白")
        if not self.schema_version.strip():
            errors.append(f"{label} schema_version 不可空白")
        if self.available_at.tzinfo is None:
            errors.append(f"{label} available_at 必須含時區")
        if not _valid_sha256(self.payload_sha256):
            errors.append(f"{label} payload_sha256 無效")
        return errors

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["available_at"] = self.available_at.isoformat()
        return payload


@dataclass(frozen=True)
class PrematchExperimentRecord:
    """One immutable historical prematch row shared by M0/M1/M2/M3.

    The observed score is a post-match label. All model inputs are represented by
    snapshot references whose ``available_at`` must be no later than ``cutoff``.
    This makes leakage checks explicit and auditable.
    """

    match_id: str
    competition: str
    event_at: datetime
    cutoff: datetime
    venue_mode: VenueMode
    dataset_role: DatasetRole
    evaluation_block: str
    experiment_id: str
    football_snapshot: SnapshotRef
    qimen_snapshot: SnapshotRef
    meihua_snapshot: SnapshotRef
    actual_home_goals: int
    actual_away_goals: int

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.match_id.strip():
            errors.append("match_id 不可空白")
        if not self.competition.strip():
            errors.append(f"{self.match_id or '<unknown>'} competition 不可空白")
        if self.event_at.tzinfo is None or self.cutoff.tzinfo is None:
            errors.append(f"{self.match_id or '<unknown>'} event_at/cutoff 必須含時區")
        elif self.cutoff >= self.event_at:
            errors.append(f"{self.match_id or '<unknown>'} cutoff 必須早於 event_at")
        if self.venue_mode not in {"TRUE_HOME", "NEUTRAL"}:
            errors.append(f"{self.match_id or '<unknown>'} venue_mode 無效")
        if self.dataset_role not in VALID_DATASET_ROLES:
            errors.append(f"{self.match_id or '<unknown>'} dataset_role 無效")
        if not self.experiment_id.strip():
            errors.append(f"{self.match_id or '<unknown>'} experiment_id 不可空白")
        if not self.evaluation_block.strip():
            errors.append(f"{self.match_id or '<unknown>'} evaluation_block 不可空白")
        for label, snapshot in (
            ("football_snapshot", self.football_snapshot),
            ("qimen_snapshot", self.qimen_snapshot),
            ("meihua_snapshot", self.meihua_snapshot),
        ):
            errors.extend(snapshot.validate(label))
            if snapshot.available_at.tzinfo is not None and self.cutoff.tzinfo is not None:
                if snapshot.available_at > self.cutoff:
                    errors.append(f"{self.match_id or '<unknown>'} {label} 在 cutoff 後才可得，存在 leakage")
        for label, value in (
            ("actual_home_goals", self.actual_home_goals),
            ("actual_away_goals", self.actual_away_goals),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                errors.append(f"{self.match_id or '<unknown>'} {label} 必須為非負整數")
        return errors

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["event_at"] = self.event_at.isoformat()
        payload["cutoff"] = self.cutoff.isoformat()
        payload["football_snapshot"] = self.football_snapshot.to_dict()
        payload["qimen_snapshot"] = self.qimen_snapshot.to_dict()
        payload["meihua_snapshot"] = self.meihua_snapshot.to_dict()
        return payload

    @property
    def fingerprint_sha256(self) -> str:
        return sha256_payload({"schema_version": EXPERIMENT_SCHEMA_VERSION, **self.to_dict()})


@dataclass(frozen=True)
class ModelForecast:
    match_id: str
    model_family: ModelFamily
    model_version: str
    home_win_probability: float
    draw_probability: float
    away_win_probability: float
    expected_home_goals: float
    expected_away_goals: float
    score_grid: tuple[tuple[int, int, float], ...]
    artifact_sources: tuple[str, ...] = ()

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.match_id.strip():
            errors.append("forecast match_id 不可空白")
        if self.model_family not in VALID_MODEL_FAMILIES:
            errors.append(f"{self.match_id or '<unknown>'} model_family 無效")
        if not self.model_version.strip():
            errors.append(f"{self.match_id or '<unknown>'} model_version 不可空白")
        probabilities = (
            self.home_win_probability,
            self.draw_probability,
            self.away_win_probability,
        )
        if any(not isfinite(value) or value < 0 or value > 1 for value in probabilities):
            errors.append(f"{self.match_id or '<unknown>'} 1X2 機率必須是 0–1 有限數")
        if all(isfinite(value) for value in probabilities) and abs(sum(probabilities) - 1.0) > 1e-9:
            errors.append(f"{self.match_id or '<unknown>'} 1X2 機率總和必須為 1")
        for label, value in (
            ("expected_home_goals", self.expected_home_goals),
            ("expected_away_goals", self.expected_away_goals),
        ):
            if not isfinite(value) or value <= 0:
                errors.append(f"{self.match_id or '<unknown>'} {label} 必須為有限正數")
        seen_scores: set[tuple[int, int]] = set()
        total = 0.0
        for home_goals, away_goals, probability in self.score_grid:
            score = (home_goals, away_goals)
            if score in seen_scores:
                errors.append(f"{self.match_id or '<unknown>'} score_grid 含重複比分 {score}")
            seen_scores.add(score)
            if (
                isinstance(home_goals, bool)
                or isinstance(away_goals, bool)
                or not isinstance(home_goals, int)
                or not isinstance(away_goals, int)
                or home_goals < 0
                or away_goals < 0
            ):
                errors.append(f"{self.match_id or '<unknown>'} score_grid 比分必須為非負整數")
            if not isfinite(probability) or probability < 0 or probability > 1:
                errors.append(f"{self.match_id or '<unknown>'} score_grid 機率無效")
            else:
                total += probability
        if not self.score_grid:
            errors.append(f"{self.match_id or '<unknown>'} score_grid 不可空白")
        elif abs(total - 1.0) > 1e-8:
            errors.append(f"{self.match_id or '<unknown>'} score_grid 機率總和必須為 1")
        return errors


@dataclass(frozen=True)
class ForecastEvaluation:
    match_id: str
    model_family: ModelFamily
    actual_result: str
    predicted_result: str
    actual_result_probability: float
    result_log_loss: float
    brier_score: float
    ranked_probability_score: float
    exact_score_probability: float
    exact_score_nll: float
    top1_result_correct: bool
    exact_score_top1_hit: bool
    exact_score_top3_hit: bool
    home_win_probability: float
    draw_probability: float
    away_win_probability: float


def _actual_result(home_goals: int, away_goals: int) -> str:
    if home_goals > away_goals:
        return "HOME"
    if home_goals < away_goals:
        return "AWAY"
    return "DRAW"


def evaluate_forecast(record: PrematchExperimentRecord, forecast: ModelForecast) -> ForecastEvaluation:
    errors = [*record.validate(), *forecast.validate()]
    if record.match_id != forecast.match_id:
        errors.append("record 與 forecast 的 match_id 不一致")
    if errors:
        raise ValueError("；".join(errors))

    labels = ("HOME", "DRAW", "AWAY")
    probabilities = (
        forecast.home_win_probability,
        forecast.draw_probability,
        forecast.away_win_probability,
    )
    actual = _actual_result(record.actual_home_goals, record.actual_away_goals)
    observed = tuple(1.0 if label == actual else 0.0 for label in labels)
    actual_index = labels.index(actual)
    actual_probability = probabilities[actual_index]
    brier = sum((probability - target) ** 2 for probability, target in zip(probabilities, observed))
    rps = sum(
        (sum(probabilities[: index + 1]) - sum(observed[: index + 1])) ** 2
        for index in range(len(labels) - 1)
    ) / (len(labels) - 1)
    ranked_results = sorted(zip(labels, probabilities), key=lambda item: item[1], reverse=True)
    ranked_scores = sorted(forecast.score_grid, key=lambda cell: cell[2], reverse=True)
    actual_score = (record.actual_home_goals, record.actual_away_goals)
    exact_probability = next(
        (probability for home, away, probability in forecast.score_grid if (home, away) == actual_score),
        0.0,
    )

    return ForecastEvaluation(
        match_id=record.match_id,
        model_family=forecast.model_family,
        actual_result=actual,
        predicted_result=ranked_results[0][0],
        actual_result_probability=actual_probability,
        result_log_loss=-log(max(actual_probability, 1e-15)),
        brier_score=brier,
        ranked_probability_score=rps,
        exact_score_probability=exact_probability,
        exact_score_nll=-log(max(exact_probability, 1e-15)),
        top1_result_correct=ranked_results[0][0] == actual,
        exact_score_top1_hit=bool(ranked_scores and ranked_scores[0][:2] == actual_score),
        exact_score_top3_hit=actual_score in tuple(cell[:2] for cell in ranked_scores[:3]),
        home_win_probability=forecast.home_win_probability,
        draw_probability=forecast.draw_probability,
        away_win_probability=forecast.away_win_probability,
    )


def validate_chronological_dataset(records: Iterable[PrematchExperimentRecord]) -> tuple[PrematchExperimentRecord, ...]:
    rows = tuple(sorted(records, key=lambda row: (row.event_at, row.match_id)))
    if not rows:
        raise ValueError("historical experiment 至少需要一場比賽")
    errors = [error for row in rows for error in row.validate()]
    ids = [row.match_id.strip() for row in rows]
    if len(set(ids)) != len(ids):
        errors.append("historical experiment 含重複 match_id")
    experiment_ids = {row.experiment_id.strip() for row in rows}
    if len(experiment_ids) != 1:
        errors.append("同一 historical experiment 必須使用單一 experiment_id")

    role_rank = {role: index for index, role in enumerate(VALID_DATASET_ROLES)}
    ranks = [role_rank[row.dataset_role] for row in rows]
    if any(current > following for current, following in zip(ranks, ranks[1:])):
        errors.append("dataset_role 必須依 TRAIN → VALIDATION → CALIBRATION → TEST_UNTOUCHED 排列")
    for role in VALID_DATASET_ROLES:
        if not any(row.dataset_role == role for row in rows):
            errors.append(f"historical experiment 缺少 {role} 區段")

    if errors:
        raise ValueError("；".join(errors))
    return rows


def aggregate_evaluations(
    evaluations: Iterable[ForecastEvaluation],
    *,
    calibration_bins: int = 10,
) -> dict[str, Any]:
    rows = tuple(evaluations)
    if not rows:
        raise ValueError("至少需要一筆 ForecastEvaluation")
    if calibration_bins < 2:
        raise ValueError("calibration_bins 至少為 2")
    families = {row.model_family for row in rows}
    if len(families) != 1:
        raise ValueError("aggregate_evaluations 一次只能彙總單一 model_family")

    count = len(rows)
    labels = ("HOME", "DRAW", "AWAY")
    probability_by_label = {
        "HOME": lambda row: row.home_win_probability,
        "DRAW": lambda row: row.draw_probability,
        "AWAY": lambda row: row.away_win_probability,
    }
    classwise_ece: dict[str, float] = {}
    classwise_recall: dict[str, float] = {}
    for label in labels:
        ece = 0.0
        for bin_index in range(calibration_bins):
            lower = bin_index / calibration_bins
            upper = (bin_index + 1) / calibration_bins
            bucket = [
                row
                for row in rows
                if lower <= probability_by_label[label](row) < upper
                or (bin_index == calibration_bins - 1 and probability_by_label[label](row) == 1.0)
            ]
            if not bucket:
                continue
            confidence = sum(probability_by_label[label](row) for row in bucket) / len(bucket)
            frequency = sum(row.actual_result == label for row in bucket) / len(bucket)
            ece += len(bucket) / count * abs(confidence - frequency)
        classwise_ece[label] = ece
        actual_count = sum(row.actual_result == label for row in rows)
        classwise_recall[label] = (
            sum(row.actual_result == label and row.predicted_result == label for row in rows) / actual_count
            if actual_count
            else 0.0
        )

    return {
        "model_family": next(iter(families)),
        "matches": count,
        "accuracy": sum(row.top1_result_correct for row in rows) / count,
        "mean_result_log_loss": sum(row.result_log_loss for row in rows) / count,
        "mean_brier_score": sum(row.brier_score for row in rows) / count,
        "mean_ranked_probability_score": sum(row.ranked_probability_score for row in rows) / count,
        "mean_exact_score_nll": sum(row.exact_score_nll for row in rows) / count,
        "exact_score_top1_accuracy": sum(row.exact_score_top1_hit for row in rows) / count,
        "exact_score_top3_accuracy": sum(row.exact_score_top3_hit for row in rows) / count,
        "classwise_recall": classwise_recall,
        "classwise_ece": classwise_ece,
        "max_classwise_ece": max(classwise_ece.values()),
    }


def paired_model_comparison(
    baseline: Iterable[ForecastEvaluation],
    challenger: Iterable[ForecastEvaluation],
) -> dict[str, Any]:
    baseline_by_id = {row.match_id: row for row in baseline}
    challenger_by_id = {row.match_id: row for row in challenger}
    if not baseline_by_id or not challenger_by_id:
        raise ValueError("paired comparison 兩側都必須有資料")
    if set(baseline_by_id) != set(challenger_by_id):
        raise ValueError("paired comparison 必須使用完全相同的 match_id")
    challenger_families = {row.model_family for row in challenger_by_id.values()}
    baseline_families = {row.model_family for row in baseline_by_id.values()}
    if len(baseline_families) != 1 or len(challenger_families) != 1:
        raise ValueError("paired comparison 每側只能包含單一 model_family")

    match_ids = sorted(baseline_by_id)
    deltas = {
        "result_log_loss_delta": [
            challenger_by_id[match_id].result_log_loss - baseline_by_id[match_id].result_log_loss
            for match_id in match_ids
        ],
        "brier_score_delta": [
            challenger_by_id[match_id].brier_score - baseline_by_id[match_id].brier_score
            for match_id in match_ids
        ],
        "ranked_probability_score_delta": [
            challenger_by_id[match_id].ranked_probability_score
            - baseline_by_id[match_id].ranked_probability_score
            for match_id in match_ids
        ],
        "exact_score_nll_delta": [
            challenger_by_id[match_id].exact_score_nll - baseline_by_id[match_id].exact_score_nll
            for match_id in match_ids
        ],
    }
    return {
        "baseline_family": next(iter(baseline_families)),
        "challenger_family": next(iter(challenger_families)),
        "matches": len(match_ids),
        **{name: sum(values) / len(values) for name, values in deltas.items()},
        "log_loss_better_match_fraction": sum(value < 0 for value in deltas["result_log_loss_delta"])
        / len(match_ids),
        "note": "所有 delta < 0 代表 challenger 較佳；比較只允許同一批 match_id。",
    }
