from __future__ import annotations

from math import isfinite
from typing import Mapping

from .outcome_features import QimenOutcomeFeatureSnapshot


QIMEN_OUTCOME_DESIGN_VERSION = "jarvis-qimen-outcome-design-v0.2.0"
DOORS = ("休門", "生門", "傷門", "杜門", "景門", "死門", "驚門", "開門")
STARS = ("天蓬", "天任", "天沖", "天輔", "天英", "天芮", "天禽", "天柱", "天心")
DEITIES = ("值符", "螣蛇", "太陰", "六合", "白虎", "玄武", "九地", "九天")
SEASONAL_STATES = ("旺", "相", "休", "囚", "廢")


def _flag(value: bool) -> float:
    return 1.0 if value else 0.0


def _reference_one_hot(prefix: str, value: str | None, categories: tuple[str, ...]) -> dict[str, float]:
    """Encode one-of-K state with the first category as the zero reference.

    Full one-hot groups sum to a constant one on every row and therefore create a
    hidden intercept even when the downstream Poisson residual model has no
    explicit intercept. Reference coding preserves the no-free-recalibration
    contract while retaining all K states through K-1 coefficients.
    """

    if value is not None and value not in categories:
        raise ValueError(f"{prefix} 有未知值：{value}")
    return {
        f"{prefix}::{category}": _flag(value == category)
        for category in categories[1:]
    }


def qimen_outcome_numeric_features(
    snapshot: QimenOutcomeFeatureSnapshot,
) -> dict[str, float]:
    """Encode a raw Qimen snapshot into a deterministic numeric design row.

    No feature in this function carries a hand-written outcome direction or goal
    weight. One-of-K categorical states use reference coding so they cannot act as
    a hidden intercept; structural patterns remain counts/flags. Star membership
    remains multi-hot because a palace can contain more than one star. The
    qualitative interpretation index is deliberately excluded.
    """

    row: dict[str, float] = {
        "same_palace": _flag(snapshot.same_palace),
        "same_visible_stem": _flag(snapshot.same_visible_stem),
        "home_is_void": _flag(snapshot.home_is_void),
        "away_is_void": _flag(snapshot.away_is_void),
        "home_is_horse": _flag(snapshot.home_is_horse),
        "away_is_horse": _flag(snapshot.away_is_horse),
        "fu_yin_count": float(snapshot.fu_yin_count),
        "fan_yin_count": float(snapshot.fan_yin_count),
        "punishment_count": float(snapshot.punishment_count),
        "pressure_count": float(snapshot.pressure_count),
        "grave_count": float(snapshot.grave_count),
        "tianwang_count": float(snapshot.tianwang_count),
    }

    row.update(_reference_one_hot("home_door", snapshot.home_door, DOORS))
    row.update(_reference_one_hot("away_door", snapshot.away_door, DOORS))
    row.update(_reference_one_hot("chief_door", snapshot.chief_door, DOORS))

    for star in STARS:
        row[f"home_star::{star}"] = _flag(star in snapshot.home_stars)
        row[f"away_star::{star}"] = _flag(star in snapshot.away_stars)

    row.update(_reference_one_hot("home_deity", snapshot.home_deity, DEITIES))
    row.update(_reference_one_hot("away_deity", snapshot.away_deity, DEITIES))
    row.update(_reference_one_hot("home_season", snapshot.home_seasonal_state, SEASONAL_STATES))
    row.update(_reference_one_hot("away_season", snapshot.away_seasonal_state, SEASONAL_STATES))

    return dict(sorted(row.items()))


def validate_numeric_feature_row(features: Mapping[str, float]) -> None:
    if not features:
        raise ValueError("Qimen outcome feature row 不可空白")
    for name, value in features.items():
        if not name.strip():
            raise ValueError("Qimen outcome feature 名稱不可空白")
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(float(value)):
            raise ValueError(f"Qimen outcome feature {name} 必須為有限數")
