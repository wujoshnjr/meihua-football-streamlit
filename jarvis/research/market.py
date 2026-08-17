from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from math import isfinite
from typing import Any

from jarvis.provenance import sha256_payload


MARKET_BENCHMARK_VERSION = "jarvis-market-benchmark-v0.1.0"


@dataclass(frozen=True)
class MarketBenchmarkSnapshot:
    """Research-only pre-match 1X2 market snapshot.

    This is deliberately a benchmark input, not a production feature. It lets the
    experiment compare JARVIS against a strong information-aggregation baseline
    without silently leaking market probabilities into M0/M1/M2/M3.
    """

    source: str
    captured_at: datetime
    home_decimal_odds: float
    draw_decimal_odds: float
    away_decimal_odds: float

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.source.strip():
            errors.append("market source 不可空白")
        if self.captured_at.tzinfo is None:
            errors.append("market captured_at 必須含時區")
        for label, value in (
            ("home_decimal_odds", self.home_decimal_odds),
            ("draw_decimal_odds", self.draw_decimal_odds),
            ("away_decimal_odds", self.away_decimal_odds),
        ):
            if not isfinite(value) or value <= 1.0:
                errors.append(f"{label} 必須為大於 1 的有限 decimal odds")
        return errors

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["captured_at"] = self.captured_at.isoformat()
        return payload

    @property
    def payload_sha256(self) -> str:
        return sha256_payload({"schema_version": MARKET_BENCHMARK_VERSION, **self.to_dict()})

    def de_vig_probabilities(self) -> tuple[float, float, float]:
        errors = self.validate()
        if errors:
            raise ValueError("；".join(errors))
        raw = (
            1.0 / self.home_decimal_odds,
            1.0 / self.draw_decimal_odds,
            1.0 / self.away_decimal_odds,
        )
        total = sum(raw)
        return tuple(value / total for value in raw)  # type: ignore[return-value]

    @property
    def overround(self) -> float:
        errors = self.validate()
        if errors:
            raise ValueError("；".join(errors))
        return (
            1.0 / self.home_decimal_odds
            + 1.0 / self.draw_decimal_odds
            + 1.0 / self.away_decimal_odds
            - 1.0
        )
