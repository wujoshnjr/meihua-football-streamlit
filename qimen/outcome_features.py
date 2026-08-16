from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal

from .football import FootballReading
from .models import QimenBoard


QIMEN_OUTCOME_FEATURE_VERSION = "jarvis-qimen-outcome-features-v0.1.0"
DirectionResolution = Literal["NORMAL", "LOW_SAME_PALACE"]


@dataclass(frozen=True)
class QimenOutcomeFeatureSnapshot:
    """Raw, versioned Qimen facts for later outcome-model training.

    These fields deliberately do not contain hand-written goal, xG, 1X2 or score
    weights. They preserve the information needed to test whether a Qimen pattern
    adds predictive value after the football-only baseline has been fitted.
    """

    feature_version: str
    home_original_stem: str
    away_original_stem: str
    home_visible_stem: str
    away_visible_stem: str
    home_palace: int
    away_palace: int
    same_palace: bool
    same_visible_stem: bool
    direction_resolution: DirectionResolution
    home_door: str | None
    away_door: str | None
    home_stars: tuple[str, ...]
    away_stars: tuple[str, ...]
    home_deity: str | None
    away_deity: str | None
    home_seasonal_state: str
    away_seasonal_state: str
    home_is_void: bool
    away_is_void: bool
    home_is_horse: bool
    away_is_horse: bool
    home_interpretation_index: int
    away_interpretation_index: int
    chief_star: str
    chief_star_palace: int
    chief_door: str
    chief_door_palace: int
    fu_yin_count: int
    fan_yin_count: int
    punishment_count: int
    pressure_count: int
    grave_count: int
    tianwang_count: int
    pattern_names: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _count_pattern(names: tuple[str, ...], predicate) -> int:
    return sum(1 for name in names if predicate(name))


def build_qimen_outcome_feature_snapshot(
    board: QimenBoard,
    reading: FootballReading,
) -> QimenOutcomeFeatureSnapshot:
    """Encode Qimen structure as raw model inputs without outcome assumptions."""

    home_palace = board.palaces[reading.home.palace]
    away_palace = board.palaces[reading.away.palace]
    pattern_names = tuple(sorted(pattern.name for pattern in board.patterns))
    same_palace = reading.home.palace == reading.away.palace

    return QimenOutcomeFeatureSnapshot(
        feature_version=QIMEN_OUTCOME_FEATURE_VERSION,
        home_original_stem=board.calendar.day_ganzhi[0],
        away_original_stem=board.calendar.hour_ganzhi[0],
        home_visible_stem=reading.home.stem,
        away_visible_stem=reading.away.stem,
        home_palace=reading.home.palace,
        away_palace=reading.away.palace,
        same_palace=same_palace,
        same_visible_stem=reading.home.stem == reading.away.stem,
        direction_resolution="LOW_SAME_PALACE" if same_palace else "NORMAL",
        home_door=reading.home.door,
        away_door=reading.away.door,
        home_stars=reading.home.stars,
        away_stars=reading.away.stars,
        home_deity=reading.home.deity,
        away_deity=reading.away.deity,
        home_seasonal_state=reading.home.seasonal_state,
        away_seasonal_state=reading.away.seasonal_state,
        home_is_void=home_palace.is_void,
        away_is_void=away_palace.is_void,
        home_is_horse=home_palace.is_horse,
        away_is_horse=away_palace.is_horse,
        home_interpretation_index=reading.home.signal_index,
        away_interpretation_index=reading.away.signal_index,
        chief_star=board.chief_star,
        chief_star_palace=board.chief_star_palace,
        chief_door=board.chief_door,
        chief_door_palace=board.chief_door_palace,
        fu_yin_count=_count_pattern(pattern_names, lambda name: "伏吟" in name),
        fan_yin_count=_count_pattern(pattern_names, lambda name: "反吟" in name),
        punishment_count=_count_pattern(pattern_names, lambda name: "擊刑" in name or name == "刑格"),
        pressure_count=_count_pattern(pattern_names, lambda name: name in {"門迫", "宮迫"}),
        grave_count=_count_pattern(pattern_names, lambda name: "入墓" in name),
        tianwang_count=_count_pattern(pattern_names, lambda name: "天網" in name),
        pattern_names=pattern_names,
    )
