from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from math import exp, isfinite, log
from typing import Iterable, Literal

from jarvis.provenance import sha256_payload

from .experiment import VALID_MODEL_FAMILIES, ModelFamily, ModelForecast
from .market import MarketBenchmarkSnapshot


MARKET_INCREMENTAL_VALUE_VERSION = "jarvis-market-incremental-value-v0.1.0"
ActualResult = Literal["HOME", "DRAW", "AWAY"]


@dataclass(frozen=True)
class MarketIncrementalObservation:
    """One VALIDATION-only structural forecast paired with a prematch market snapshot."""

    match_id: str
    event_at: datetime
    cutoff_at: datetime
    model_family: ModelFamily
    model_version: str
    model_probabilities: tuple[float, float, float]
    market_snapshot: MarketBenchmarkSnapshot
    actual_result: ActualResult
    dataset_role: str = "VALIDATION"

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.match_id.strip():
            errors.append("market incremental observation 的 match_id 不可空白")
        if self.event_at.tzinfo is None or self.cutoff_at.tzinfo is None:
            errors.append(f"{self.match_id} 的 event_at/cutoff_at 必須含時區")
        elif self.cutoff_at >= self.event_at:
            errors.append(f"{self.match_id} 的 cutoff_at 必須早於 event_at")
        if self.dataset_role != "VALIDATION":
            errors.append(f"{self.match_id} 不是 VALIDATION，不可選 market pooling weight")
        if self.model_family not in VALID_MODEL_FAMILIES:
            errors.append(f"{self.match_id} 的 model_family 無效")
        if not self.model_version.strip():
            errors.append(f"{self.match_id} 的 model_version 不可空白")
        if self.actual_result not in {"HOME", "DRAW", "AWAY"}:
            errors.append(f"{self.match_id} 的 actual_result 無效")
        if any(not isfinite(value) or value <= 0 or value >= 1 for value in self.model_probabilities):
            errors.append(f"{self.match_id} 的 structural 1X2 機率必須嚴格介於 0 與 1")
        elif abs(sum(self.model_probabilities) - 1.0) > 1e-9:
            errors.append(f"{self.match_id} 的 structural 1X2 機率總和必須為 1")
        market_errors = self.market_snapshot.validate()
        errors.extend(f"{self.match_id}: {error}" for error in market_errors)
        if self.market_snapshot.captured_at.tzinfo is not None and self.cutoff_at.tzinfo is not None:
            if self.market_snapshot.captured_at > self.cutoff_at:
                errors.append(f"{self.match_id} 的 market snapshot 在 cutoff 後才取得，存在 leakage")
        return errors

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["event_at"] = self.event_at.isoformat()
        payload["cutoff_at"] = self.cutoff_at.isoformat()
        payload["market_snapshot"] = self.market_snapshot.to_dict()
        return payload


@dataclass(frozen=True)
class MarketPoolCandidate:
    structural_weight: float
    matches: int
    mean_log_loss: float
    mean_brier_score: float
    mean_ranked_probability_score: float


@dataclass(frozen=True)
class MarketIncrementalValueFit:
    schema_version: str
    model_family: ModelFamily
    model_version: str
    selected_structural_weight: float
    validation_matches: int
    validation_started_at: datetime
    validation_ended_at: datetime
    candidates: tuple[MarketPoolCandidate, ...]
    validation_data_sha256: str
    artifact_sha256: str

    @property
    def adds_incremental_value(self) -> bool:
        return self.selected_structural_weight > 0.0

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["validation_started_at"] = self.validation_started_at.isoformat()
        payload["validation_ended_at"] = self.validation_ended_at.isoformat()
        payload["adds_incremental_value"] = self.adds_incremental_value
        return payload


def logarithmic_pool(
    structural_probabilities: tuple[float, float, float],
    market_probabilities: tuple[float, float, float],
    structural_weight: float,
) -> tuple[float, float, float]:
    """Combine two strictly positive 1X2 distributions with a logarithmic opinion pool."""

    if not isfinite(structural_weight) or not 0 <= structural_weight <= 1:
        raise ValueError("structural_weight 必須介於 0 與 1")
    for label, probabilities in (
        ("structural", structural_probabilities),
        ("market", market_probabilities),
    ):
        if any(not isfinite(value) or value <= 0 or value >= 1 for value in probabilities):
            raise ValueError(f"{label} 1X2 機率必須嚴格介於 0 與 1")
        if abs(sum(probabilities) - 1.0) > 1e-9:
            raise ValueError(f"{label} 1X2 機率總和必須為 1")

    log_weights = [
        structural_weight * log(structural) + (1.0 - structural_weight) * log(market)
        for structural, market in zip(structural_probabilities, market_probabilities)
    ]
    anchor = max(log_weights)
    unnormalized = [exp(value - anchor) for value in log_weights]
    total = sum(unnormalized)
    return tuple(value / total for value in unnormalized)  # type: ignore[return-value]


def _losses(probabilities: tuple[float, float, float], actual_result: ActualResult) -> tuple[float, float, float]:
    actual_index = {"HOME": 0, "DRAW": 1, "AWAY": 2}[actual_result]
    observed = tuple(1.0 if index == actual_index else 0.0 for index in range(3))
    log_loss = -log(max(probabilities[actual_index], 1e-15))
    brier = sum((probability - target) ** 2 for probability, target in zip(probabilities, observed))
    rps = sum(
        (sum(probabilities[: index + 1]) - sum(observed[: index + 1])) ** 2
        for index in range(2)
    ) / 2.0
    return log_loss, brier, rps


def fit_market_incremental_value(
    observations: Iterable[MarketIncrementalObservation],
    *,
    structural_weight_grid: Iterable[float] = tuple(index / 20 for index in range(21)),
    min_matches: int = 50,
) -> MarketIncrementalValueFit:
    """Select structural-vs-market log-pool weight on VALIDATION only.

    Zero structural weight is mandatory so the market-only forecast always remains
    a legal fallback. Weight one is also mandatory so model-only performance is
    explicitly represented in the candidate table. Selection minimizes 1X2 log
    loss, then Brier and RPS; exact ties conservatively prefer less structural weight.
    """

    rows = sorted(observations, key=lambda row: (row.event_at, row.match_id))
    if len(rows) < min_matches:
        raise ValueError(f"market incremental validation 至少需要 {min_matches} 場")
    errors = [error for row in rows for error in row.validate()]
    if errors:
        raise ValueError("；".join(errors))
    if len({row.match_id.strip() for row in rows}) != len(rows):
        raise ValueError("market incremental validation 含重複 match_id")
    model_families = {row.model_family for row in rows}
    model_versions = {row.model_version.strip() for row in rows}
    if len(model_families) != 1 or len(model_versions) != 1:
        raise ValueError("一次 market incremental fit 只能評估單一 model_family/model_version")

    grid = tuple(sorted(set(float(value) for value in structural_weight_grid)))
    if not grid or any(not isfinite(value) or not 0 <= value <= 1 for value in grid):
        raise ValueError("structural_weight_grid 必須全部介於 0 與 1")
    if 0.0 not in grid:
        raise ValueError("structural_weight_grid 必須包含 0，保留 market-only fallback")
    if 1.0 not in grid:
        raise ValueError("structural_weight_grid 必須包含 1，保留 model-only benchmark")

    candidates: list[MarketPoolCandidate] = []
    for structural_weight in grid:
        log_losses: list[float] = []
        briers: list[float] = []
        rps_values: list[float] = []
        for row in rows:
            probabilities = logarithmic_pool(
                row.model_probabilities,
                row.market_snapshot.de_vig_probabilities(),
                structural_weight,
            )
            log_loss, brier, rps = _losses(probabilities, row.actual_result)
            log_losses.append(log_loss)
            briers.append(brier)
            rps_values.append(rps)
        candidates.append(
            MarketPoolCandidate(
                structural_weight=structural_weight,
                matches=len(rows),
                mean_log_loss=sum(log_losses) / len(rows),
                mean_brier_score=sum(briers) / len(rows),
                mean_ranked_probability_score=sum(rps_values) / len(rows),
            )
        )

    ordered = tuple(
        sorted(
            candidates,
            key=lambda candidate: (
                candidate.mean_log_loss,
                candidate.mean_brier_score,
                candidate.mean_ranked_probability_score,
                candidate.structural_weight,
            ),
        )
    )
    selected = ordered[0]
    validation_data = [row.to_dict() for row in rows]
    validation_data_sha256 = sha256_payload(validation_data)
    core = {
        "schema_version": MARKET_INCREMENTAL_VALUE_VERSION,
        "model_family": rows[0].model_family,
        "model_version": rows[0].model_version.strip(),
        "selected_structural_weight": selected.structural_weight,
        "validation_matches": len(rows),
        "validation_started_at": rows[0].event_at.isoformat(),
        "validation_ended_at": rows[-1].event_at.isoformat(),
        "candidates": [asdict(candidate) for candidate in ordered],
        "validation_data_sha256": validation_data_sha256,
    }
    return MarketIncrementalValueFit(
        schema_version=MARKET_INCREMENTAL_VALUE_VERSION,
        model_family=rows[0].model_family,
        model_version=rows[0].model_version.strip(),
        selected_structural_weight=selected.structural_weight,
        validation_matches=len(rows),
        validation_started_at=rows[0].event_at,
        validation_ended_at=rows[-1].event_at,
        candidates=ordered,
        validation_data_sha256=validation_data_sha256,
        artifact_sha256=sha256_payload(core),
    )


def apply_market_incremental_fit(
    forecast: ModelForecast,
    market_snapshot: MarketBenchmarkSnapshot,
    fit: MarketIncrementalValueFit,
    *,
    cutoff_at: datetime,
) -> tuple[float, float, float]:
    """Apply a frozen research-only market pool after model/market provenance checks."""

    forecast_errors = forecast.validate()
    if forecast_errors:
        raise ValueError("；".join(forecast_errors))
    market_errors = market_snapshot.validate()
    if market_errors:
        raise ValueError("；".join(market_errors))
    if cutoff_at.tzinfo is None:
        raise ValueError("cutoff_at 必須含時區")
    if market_snapshot.captured_at > cutoff_at:
        raise ValueError("market snapshot 在 cutoff 後才取得，存在 leakage")
    if forecast.model_family != fit.model_family or forecast.model_version != fit.model_version:
        raise ValueError("forecast model_family/model_version 與 market incremental fit 不一致")
    return logarithmic_pool(
        (
            forecast.home_win_probability,
            forecast.draw_probability,
            forecast.away_win_probability,
        ),
        market_snapshot.de_vig_probabilities(),
        fit.selected_structural_weight,
    )
