from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from jarvis.research.market import MarketBenchmarkSnapshot


def test_de_vig_probabilities_sum_to_one_and_remove_margin():
    snapshot = MarketBenchmarkSnapshot(
        source="fixture-market",
        captured_at=datetime(2026, 1, 1, 12, tzinfo=ZoneInfo("UTC")),
        home_decimal_odds=2.0,
        draw_decimal_odds=3.5,
        away_decimal_odds=4.0,
    )
    probabilities = snapshot.de_vig_probabilities()
    assert sum(probabilities) == pytest.approx(1.0)
    assert snapshot.overround > 0
    assert len(snapshot.payload_sha256) == 64


def test_invalid_market_odds_are_rejected():
    snapshot = MarketBenchmarkSnapshot(
        source="fixture-market",
        captured_at=datetime(2026, 1, 1, 12, tzinfo=ZoneInfo("UTC")),
        home_decimal_odds=1.0,
        draw_decimal_odds=3.0,
        away_decimal_odds=4.0,
    )
    with pytest.raises(ValueError, match="大於 1"):
        snapshot.de_vig_probabilities()
