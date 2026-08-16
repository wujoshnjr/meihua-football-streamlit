from __future__ import annotations

from math import isfinite
from typing import Mapping

from .outcome_features import QimenOutcomeFeatureSnapshot


QIMEN_OUTCOME_DESIGN_VERSION = "jarvis-qimen-outcome-design-v0.1.0"
DOORS = ("休門", "生門", "傷門", "杜門", "景門", "死門", "驚門", "開門")
STARS = ("天蓬", "天任", "天沖", "天輔", "天英", "天芮", "天禽", "天柱", "天心")
DEITIES = ("值符", "螣蛇", "太陰", "六合", "白虎", "玄武", "九地", "九天")
SEASONAL_STATES = ("旺", "相", "休", "囚", "廢")


def _flag(value: bool) -> float:
    return 1.0 if value else 0.0


def qimen_outcome_numeric_features(
    snapshot: QimenOutcomeFeatureSnapshot,
) -> dict[str, float]:
    """Encode a raw Qimen snapshot into a deterministic numeric design row.

    No feature in this function carries a hand-written outcome direction or goal
    weight. Categorical states are one-hot encoded and structural patterns remain
    counts/flags. The qualitative interpretation index is deliberately excluded.
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

    for door in DOORS:
        row[f"home_door::{door}"] = _flag(snapshot.home_door == door)
        row[f"away_door::{door}"] = _flag(snapshot.away_door == door)
        row[f"chief_door::{door}"] = _flag(snapshot.chief_door == door)
    for star in STARS:
        row[f"home_star::{star}"] = _flag(star in snapshot.home_stars)
        row[f"away_star::{star}"] = _flag(star in snapshot.away_stars)
    for deity in DEITIES:
        row[f"home_deity::{deity}"] = _flag(snapshot.home_deity == deity)
        row[f"away_deity::{deity}"] = _flag(snapshot.away_deity == deity)
    for state in SEASONAL_STATES:
        row[f"home_season::{state}"] = _flag(snapshot.home_seasonal_state == state)
        row[f"away_season::{state}"] = _flag(snapshot.away_seasonal_state == state)

    return row


def validate_numeric_feature_row(features: Mapping[str, float]) -> None:
    if not features:
        raise ValueError("Qimen outcome feature row 不可空白")
    for name, value in features.items():
        if not name.strip():
            raise ValueError("Qimen outcome feature 名稱不可空白")
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(float(value)):
            raise ValueError(f"Qimen outcome feature {name} 必須為有限數")
