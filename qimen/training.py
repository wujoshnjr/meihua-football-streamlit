from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from math import exp, isfinite, log
from typing import Any, Iterable

from .integrity import sha256_payload
from .runtime import detect_git_commit


SPLIT_VERSION = "jarvis-chronological-split-v1.0.0"
DIXON_COLES_FIT_VERSION = "jarvis-dixon-coles-rho-fit-v1.0.0"
TEMPERATURE_FIT_VERSION = "jarvis-temperature-scaling-v1.0.0"
OUTCOME_LABELS = ("主勝", "和局", "客勝")


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and all(character in "0123456789abcdef" for character in value)


@dataclass(frozen=True)
class ChronologicalSample:
    match_id: str
    event_at: datetime
    competition: str
    evaluation_block: str
    payload_sha256: str

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.match_id.strip():
            errors.append("match_id 不可空白")
        if self.event_at.tzinfo is None:
            errors.append(f"{self.match_id} 的 event_at 必須含時區")
        if not self.competition.strip() or not self.evaluation_block.strip():
            errors.append(f"{self.match_id} 必須保存 competition 與 evaluation_block")
        if not _is_sha256(self.payload_sha256):
            errors.append(f"{self.match_id} 的 payload_sha256 無效")
        return errors

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["event_at"] = self.event_at.isoformat()
        return payload


@dataclass(frozen=True)
class ChronologicalSplitManifest:
    schema_version: str
    experiment_id: str
    git_commit: str
    train_end: datetime
    validation_end: datetime
    calibration_end: datetime
    assignments: tuple[dict[str, Any], ...]
    counts: dict[str, int]
    source_payload_sha256: str
    test_set_sha256: str
    fingerprint_sha256: str

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        for key in ("train_end", "validation_end", "calibration_end"):
            payload[key] = getattr(self, key).isoformat()
        return payload


def build_chronological_split_manifest(
    samples: Iterable[ChronologicalSample],
    *,
    experiment_id: str,
    train_end: datetime,
    validation_end: datetime,
    calibration_end: datetime,
) -> ChronologicalSplitManifest:
    """Assign four immutable, non-overlapping chronological dataset roles."""

    if not experiment_id.strip():
        raise ValueError("experiment_id 不可空白")
    boundaries = (train_end, validation_end, calibration_end)
    if any(value.tzinfo is None for value in boundaries):
        raise ValueError("所有時序切分界線必須含時區")
    if not train_end < validation_end < calibration_end:
        raise ValueError("切分界線必須嚴格依 TRAIN → VALIDATION → CALIBRATION 排列")

    rows = sorted(samples, key=lambda item: (item.event_at, item.match_id))
    if not rows:
        raise ValueError("至少需要一筆歷史樣本")
    errors = [error for row in rows for error in row.validate()]
    if errors:
        raise ValueError("；".join(errors))
    match_ids = [row.match_id.strip() for row in rows]
    if len(match_ids) != len(set(match_ids)):
        raise ValueError("歷史樣本含重複 match_id")

    assignments: list[dict[str, Any]] = []
    counts = {role: 0 for role in ("TRAIN", "VALIDATION", "CALIBRATION", "TEST_UNTOUCHED")}
    for row in rows:
        role = (
            "TRAIN"
            if row.event_at <= train_end
            else "VALIDATION"
            if row.event_at <= validation_end
            else "CALIBRATION"
            if row.event_at <= calibration_end
            else "TEST_UNTOUCHED"
        )
        counts[role] += 1
        assignments.append({
            **row.to_dict(),
            "dataset_role": role,
            "experiment_id": experiment_id.strip(),
        })
    empty_roles = [role for role, count in counts.items() if count == 0]
    if empty_roles:
        raise ValueError("四層切分每層都必須有資料；空層：" + "、".join(empty_roles))

    source_payload_sha256 = sha256_payload([row.to_dict() for row in rows])
    test_rows = [row for row in assignments if row["dataset_role"] == "TEST_UNTOUCHED"]
    core = {
        "schema_version": SPLIT_VERSION,
        "experiment_id": experiment_id.strip(),
        "git_commit": detect_git_commit(),
        "train_end": train_end.isoformat(),
        "validation_end": validation_end.isoformat(),
        "calibration_end": calibration_end.isoformat(),
        "assignments": assignments,
        "counts": counts,
        "source_payload_sha256": source_payload_sha256,
        "test_set_sha256": sha256_payload(test_rows),
    }
    return ChronologicalSplitManifest(
        schema_version=SPLIT_VERSION,
        experiment_id=experiment_id.strip(),
        git_commit=core["git_commit"],
        train_end=train_end,
        validation_end=validation_end,
        calibration_end=calibration_end,
        assignments=tuple(assignments),
        counts=counts,
        source_payload_sha256=source_payload_sha256,
        test_set_sha256=core["test_set_sha256"],
        fingerprint_sha256=sha256_payload(core),
    )


def dixon_coles_tau(
    home_goals: int,
    away_goals: int,
    home_rate: float,
    away_rate: float,
    rho: float,
) -> float:
    if home_goals == 0 and away_goals == 0:
        return 1 - home_rate * away_rate * rho
    if home_goals == 0 and away_goals == 1:
        return 1 + home_rate * rho
    if home_goals == 1 and away_goals == 0:
        return 1 + away_rate * rho
    if home_goals == 1 and away_goals == 1:
        return 1 - rho
    return 1.0


@dataclass(frozen=True)
class DixonColesObservation:
    match_id: str
    event_at: datetime
    expected_home_goals: float
    expected_away_goals: float
    actual_home_goals: int
    actual_away_goals: int
    payload_sha256: str
    dataset_role: str = "TRAIN"

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.match_id.strip() or self.event_at.tzinfo is None:
            errors.append("Dixon–Coles 訓練樣本必須有 match_id 與含時區 event_at")
        if self.dataset_role != "TRAIN":
            errors.append(f"{self.match_id} 不是 TRAIN，不可估計 rho")
        for label, value in (
            ("主隊 lambda", self.expected_home_goals),
            ("客隊 lambda", self.expected_away_goals),
        ):
            if not isfinite(value) or value <= 0:
                errors.append(f"{self.match_id} 的{label}必須為有限正數")
        for label, value in (
            ("主隊進球", self.actual_home_goals),
            ("客隊進球", self.actual_away_goals),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                errors.append(f"{self.match_id} 的{label}必須為非負整數")
        if not _is_sha256(self.payload_sha256):
            errors.append(f"{self.match_id} 的 payload_sha256 無效")
        return errors

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["event_at"] = self.event_at.isoformat()
        return payload


@dataclass(frozen=True)
class DixonColesFit:
    schema_version: str
    rho: float
    git_commit: str
    profile_ci_lower: float
    profile_ci_upper: float
    matches: int
    low_score_matches: int
    effective_weight: float
    half_life_days: float
    training_started_at: datetime
    training_ended_at: datetime
    weighted_log_likelihood_delta: float
    training_data_sha256: str
    boundary_hit: bool
    warnings: tuple[str, ...]
    artifact_sha256: str

    @property
    def rho_source(self) -> str:
        return f"dc-rho-fit:{self.artifact_sha256}"

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["training_started_at"] = self.training_started_at.isoformat()
        payload["training_ended_at"] = self.training_ended_at.isoformat()
        payload["rho_source"] = self.rho_source
        return payload


def fit_dixon_coles_rho(
    observations: Iterable[DixonColesObservation],
    *,
    half_life_days: float = 365.0,
    rho_min: float = -0.20,
    rho_max: float = 0.20,
    grid_steps: int = 1601,
    min_matches: int = 200,
    min_low_score_matches: int = 20,
) -> DixonColesFit:
    """Fit rho on TRAIN only with deterministic exponential time decay."""

    rows = sorted(observations, key=lambda item: (item.event_at, item.match_id))
    if len(rows) < min_matches:
        raise ValueError(f"估計 rho 至少需要 {min_matches} 場 TRAIN 樣本")
    if not isfinite(half_life_days) or half_life_days <= 0:
        raise ValueError("half_life_days 必須為有限正數")
    if not isfinite(rho_min) or not isfinite(rho_max) or not rho_min < 0 < rho_max:
        raise ValueError("rho 搜尋範圍必須跨越 0")
    if isinstance(grid_steps, bool) or not isinstance(grid_steps, int) or grid_steps < 101:
        raise ValueError("rho grid_steps 至少為 101")
    errors = [error for row in rows for error in row.validate()]
    if errors:
        raise ValueError("；".join(errors))
    if len({row.match_id.strip() for row in rows}) != len(rows):
        raise ValueError("Dixon–Coles 訓練資料含重複 match_id")
    low_score_matches = sum(
        row.actual_home_goals <= 1 and row.actual_away_goals <= 1
        for row in rows
    )
    if low_score_matches < min_low_score_matches:
        raise ValueError(f"估計 rho 至少需要 {min_low_score_matches} 場 0–0／0–1／1–0／1–1 樣本")

    training_end = rows[-1].event_at
    weighted_rows = [
        (
            row,
            0.5 ** (max(0.0, (training_end - row.event_at).total_seconds()) / 86400 / half_life_days),
        )
        for row in rows
    ]
    candidates: list[tuple[float, float]] = []
    for index in range(grid_steps):
        rho = rho_min + (rho_max - rho_min) * index / (grid_steps - 1)
        score = 0.0
        valid = True
        for row, weight in weighted_rows:
            tau = dixon_coles_tau(
                row.actual_home_goals,
                row.actual_away_goals,
                row.expected_home_goals,
                row.expected_away_goals,
                rho,
            )
            if tau <= 0 or not isfinite(tau):
                valid = False
                break
            score += weight * log(tau)
        if valid:
            candidates.append((rho, score))
    if not candidates:
        raise ValueError("rho 搜尋範圍內沒有正值 Dixon–Coles 校正係數")
    best_rho, best_score = max(candidates, key=lambda item: (item[1], -abs(item[0])))
    profile_candidates = [rho for rho, score in candidates if 2 * (best_score - score) <= 3.841]
    boundary_hit = best_rho in {candidates[0][0], candidates[-1][0]}
    warnings: list[str] = []
    if boundary_hit:
        warnings.append("最佳 rho 落在搜尋邊界；應擴大 TRAIN 或重新檢查 lambda 規格，不可直接外推。")
    if profile_candidates[0] == candidates[0][0] or profile_candidates[-1] == candidates[-1][0]:
        warnings.append("rho profile likelihood 區間碰觸搜尋邊界，區間可能尚未封閉。")

    training_data = [row.to_dict() for row in rows]
    core = {
        "schema_version": DIXON_COLES_FIT_VERSION,
        "rho": best_rho,
        "git_commit": detect_git_commit(),
        "profile_ci_lower": profile_candidates[0],
        "profile_ci_upper": profile_candidates[-1],
        "matches": len(rows),
        "low_score_matches": low_score_matches,
        "effective_weight": sum(weight for _, weight in weighted_rows),
        "half_life_days": half_life_days,
        "training_started_at": rows[0].event_at.isoformat(),
        "training_ended_at": training_end.isoformat(),
        "weighted_log_likelihood_delta": best_score,
        "training_data_sha256": sha256_payload(training_data),
        "boundary_hit": boundary_hit,
        "warnings": warnings,
    }
    return DixonColesFit(
        schema_version=DIXON_COLES_FIT_VERSION,
        rho=best_rho,
        git_commit=core["git_commit"],
        profile_ci_lower=profile_candidates[0],
        profile_ci_upper=profile_candidates[-1],
        matches=len(rows),
        low_score_matches=low_score_matches,
        effective_weight=core["effective_weight"],
        half_life_days=half_life_days,
        training_started_at=rows[0].event_at,
        training_ended_at=training_end,
        weighted_log_likelihood_delta=best_score,
        training_data_sha256=core["training_data_sha256"],
        boundary_hit=boundary_hit,
        warnings=tuple(warnings),
        artifact_sha256=sha256_payload(core),
    )


def temperature_scale_probabilities(
    probabilities: tuple[float, float, float],
    temperature: float,
) -> tuple[float, float, float]:
    if not isfinite(temperature) or temperature <= 0:
        raise ValueError("temperature 必須為有限正數")
    if any(not isfinite(value) or value <= 0 for value in probabilities):
        raise ValueError("溫度校準前的三類機率必須為有限正數")
    if abs(sum(probabilities) - 1.0) > 1e-9:
        raise ValueError("溫度校準前的三類機率總和必須為 1")
    logits = [log(value) / temperature for value in probabilities]
    anchor = max(logits)
    weights = [exp(value - anchor) for value in logits]
    total = sum(weights)
    return (weights[0] / total, weights[1] / total, weights[2] / total)


@dataclass(frozen=True)
class CalibrationObservation:
    match_id: str
    event_at: datetime
    probabilities: tuple[float, float, float]
    actual_result: str
    model_spec_sha256: str
    payload_sha256: str
    dataset_role: str = "CALIBRATION"

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.match_id.strip() or self.event_at.tzinfo is None:
            errors.append("校準樣本必須有 match_id 與含時區 event_at")
        if self.dataset_role != "CALIBRATION":
            errors.append(f"{self.match_id} 不是 CALIBRATION，不可擬合校準器")
        if self.actual_result not in OUTCOME_LABELS:
            errors.append(f"{self.match_id} 的 actual_result 無效")
        try:
            temperature_scale_probabilities(self.probabilities, 1.0)
        except ValueError as exc:
            errors.append(f"{self.match_id}：{exc}")
        if not _is_sha256(self.model_spec_sha256) or not _is_sha256(self.payload_sha256):
            errors.append(f"{self.match_id} 的模型／資料指紋無效")
        return errors

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["event_at"] = self.event_at.isoformat()
        return payload


@dataclass(frozen=True)
class TemperatureCalibrationFit:
    schema_version: str
    temperature: float
    git_commit: str
    matches: int
    pre_log_loss: float
    post_log_loss: float
    calibration_started_at: datetime
    calibration_ended_at: datetime
    model_spec_sha256: str
    calibration_data_sha256: str
    warnings: tuple[str, ...]
    artifact_sha256: str

    @property
    def calibration_source(self) -> str:
        return f"temperature-fit:{self.artifact_sha256}"

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["calibration_started_at"] = self.calibration_started_at.isoformat()
        payload["calibration_ended_at"] = self.calibration_ended_at.isoformat()
        payload["calibration_source"] = self.calibration_source
        return payload


def fit_temperature_scaler(
    observations: Iterable[CalibrationObservation],
    *,
    temperature_min: float = 0.25,
    temperature_max: float = 4.0,
    grid_steps: int = 1501,
    min_matches: int = 200,
) -> TemperatureCalibrationFit:
    """Fit one temperature on CALIBRATION only; TEST_UNTOUCHED is forbidden."""

    rows = sorted(observations, key=lambda item: (item.event_at, item.match_id))
    if len(rows) < min_matches:
        raise ValueError(f"溫度校準至少需要 {min_matches} 場 CALIBRATION 樣本")
    if not 0 < temperature_min < 1 < temperature_max:
        raise ValueError("temperature 搜尋範圍必須包含 1")
    if isinstance(grid_steps, bool) or not isinstance(grid_steps, int) or grid_steps < 101 or grid_steps % 2 == 0:
        raise ValueError("temperature grid_steps 必須為至少 101 的奇數")
    errors = [error for row in rows for error in row.validate()]
    if errors:
        raise ValueError("；".join(errors))
    if len({row.match_id.strip() for row in rows}) != len(rows):
        raise ValueError("校準資料含重複 match_id")
    model_hashes = {row.model_spec_sha256 for row in rows}
    if len(model_hashes) != 1:
        raise ValueError("同一校準器只能擬合一個未校準 model_spec_sha256")

    def mean_log_loss(temperature: float) -> float:
        total = 0.0
        for row in rows:
            calibrated = temperature_scale_probabilities(row.probabilities, temperature)
            total -= log(calibrated[OUTCOME_LABELS.index(row.actual_result)])
        return total / len(rows)

    log_min = log(temperature_min)
    log_max = log(temperature_max)
    candidates = [
        exp(log_min + (log_max - log_min) * index / (grid_steps - 1))
        for index in range(grid_steps)
    ]
    scored = [(temperature, mean_log_loss(temperature)) for temperature in candidates]
    best_temperature, post_log_loss = min(scored, key=lambda item: (item[1], abs(item[0] - 1)))
    pre_log_loss = mean_log_loss(1.0)
    warnings: list[str] = []
    if best_temperature in {candidates[0], candidates[-1]}:
        warnings.append("最佳 temperature 落在搜尋邊界；需要更多 CALIBRATION 資料或重查模型規格。")
    if post_log_loss >= pre_log_loss - 1e-12:
        warnings.append("校準集未顯示 log loss 改善；正式預測應維持未校準輸出。")

    calibration_data = [row.to_dict() for row in rows]
    core = {
        "schema_version": TEMPERATURE_FIT_VERSION,
        "temperature": best_temperature,
        "git_commit": detect_git_commit(),
        "matches": len(rows),
        "pre_log_loss": pre_log_loss,
        "post_log_loss": post_log_loss,
        "calibration_started_at": rows[0].event_at.isoformat(),
        "calibration_ended_at": rows[-1].event_at.isoformat(),
        "model_spec_sha256": next(iter(model_hashes)),
        "calibration_data_sha256": sha256_payload(calibration_data),
        "warnings": warnings,
    }
    return TemperatureCalibrationFit(
        schema_version=TEMPERATURE_FIT_VERSION,
        temperature=best_temperature,
        git_commit=core["git_commit"],
        matches=len(rows),
        pre_log_loss=pre_log_loss,
        post_log_loss=post_log_loss,
        calibration_started_at=rows[0].event_at,
        calibration_ended_at=rows[-1].event_at,
        model_spec_sha256=core["model_spec_sha256"],
        calibration_data_sha256=core["calibration_data_sha256"],
        warnings=tuple(warnings),
        artifact_sha256=sha256_payload(core),
    )
