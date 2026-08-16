from __future__ import annotations

from dataclasses import asdict, dataclass
from math import isfinite
from typing import Literal


VenueMode = Literal["TRUE_HOME", "NEUTRAL"]
VENUE_BASELINE_VERSION = "jarvis-venue-baseline-v0.1.0"


@dataclass(frozen=True)
class VenueBaseline:
    """Explicit scoring baseline for a registered match venue context.

    Neutral matches must not silently inherit a league home/away scoring split.
    Their scoring means must come from an explicit, pre-match neutral-site estimate.
    """

    schema_version: str
    venue_mode: VenueMode
    home_goals_per_match: float
    away_goals_per_match: float
    source: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _validate_rate(label: str, value: float) -> None:
    if not isfinite(value) or value <= 0:
        raise ValueError(f"{label}必須為有限正數")


def resolve_venue_baseline(
    *,
    venue_mode: VenueMode,
    league_home_goals_per_match: float,
    league_away_goals_per_match: float,
    neutral_home_goals_per_match: float | None = None,
    neutral_away_goals_per_match: float | None = None,
    source: str,
) -> VenueBaseline:
    """Return an auditable baseline without inventing neutral-site home advantage.

    ``TRUE_HOME`` uses the registered league home/away means. ``NEUTRAL`` requires
    two explicit neutral-site means. The function deliberately refuses to average
    league home/away means as a fallback because that would encode an unregistered
    modelling assumption.
    """

    if venue_mode not in {"TRUE_HOME", "NEUTRAL"}:
        raise ValueError("venue_mode 必須為 TRUE_HOME 或 NEUTRAL")
    if not source.strip():
        raise ValueError("場地基準來源不可空白")

    _validate_rate("聯盟主場均進球", league_home_goals_per_match)
    _validate_rate("聯盟客場均進球", league_away_goals_per_match)

    if venue_mode == "TRUE_HOME":
        home_rate = league_home_goals_per_match
        away_rate = league_away_goals_per_match
    else:
        if neutral_home_goals_per_match is None or neutral_away_goals_per_match is None:
            raise ValueError("中立場必須提供盤前估計的 neutral 主客均值，不可沿用主場優勢")
        _validate_rate("中立場名義主隊均進球", neutral_home_goals_per_match)
        _validate_rate("中立場名義客隊均進球", neutral_away_goals_per_match)
        home_rate = neutral_home_goals_per_match
        away_rate = neutral_away_goals_per_match

    return VenueBaseline(
        schema_version=VENUE_BASELINE_VERSION,
        venue_mode=venue_mode,
        home_goals_per_match=home_rate,
        away_goals_per_match=away_rate,
        source=source.strip(),
    )
