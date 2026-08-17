from __future__ import annotations

from typing import Mapping

from .engine import MeihuaSnapshot

MEIHUA_OUTCOME_DESIGN_VERSION = "jarvis-meihua-outcome-design-v0.2.0"
TRIGRAMS = ("乾", "兌", "離", "震", "巽", "坎", "艮", "坤")
RELATIONS = ("生體", "體生用", "克體", "體克用", "比和")
SEASON_STATES = ("旺", "平", "衰")
MOVING_LINES = (1, 2, 3, 4, 5, 6)


def _reference_one_hot(prefix: str, value: str, categories: tuple[str, ...]) -> dict[str, float]:
    if value not in categories:
        raise ValueError(f"{prefix} 有未知值：{value}")
    return {
        f"{prefix}={category}": 1.0 if value == category else 0.0
        for category in categories[1:]
    }


def _moving_line_features(value: int) -> dict[str, float]:
    if value not in MOVING_LINES:
        raise ValueError(f"moving_line 有未知值：{value}")
    return {
        f"moving_line={line}": 1.0 if value == line else 0.0
        for line in MOVING_LINES[1:]
    }


def meihua_outcome_numeric_features(snapshot: MeihuaSnapshot) -> dict[str, float]:
    """Encode raw Meihua state without handwritten football direction weights.

    One-of-K fields use reference coding rather than full one-hot encoding. This
    prevents categorical groups from summing to a constant one and acting as a
    hidden intercept in the no-intercept residual model. Moving-line position is
    categorical: no linear spacing assumption is imposed on lines one through six.
    """

    features: dict[str, float] = {}
    features.update(_moving_line_features(snapshot.moving_line))
    for prefix, value in (
        ("upper_trigram", snapshot.upper_trigram),
        ("lower_trigram", snapshot.lower_trigram),
        ("body_trigram", snapshot.body_trigram),
        ("use_trigram", snapshot.use_trigram),
        ("mutual_upper_trigram", snapshot.mutual_upper_trigram),
        ("mutual_lower_trigram", snapshot.mutual_lower_trigram),
        ("changed_use_trigram", snapshot.changed_use_trigram),
    ):
        features.update(_reference_one_hot(prefix, value, TRIGRAMS))
    for prefix, value in (
        ("body_use_relation", snapshot.body_use_relation),
        ("mutual_upper_relation", snapshot.mutual_upper_relation_to_body),
        ("mutual_lower_relation", snapshot.mutual_lower_relation_to_body),
        ("changed_use_relation", snapshot.changed_use_relation_to_body),
    ):
        features.update(_reference_one_hot(prefix, value, RELATIONS))
    features.update(_reference_one_hot("body_season_state", snapshot.body_season_state, SEASON_STATES))
    return dict(sorted(features.items()))


def validate_meihua_feature_row(features: Mapping[str, float]) -> None:
    if not features:
        raise ValueError("Meihua feature row 不可空白")
    expected_prefixes = (
        "moving_line=",
        "upper_trigram=",
        "lower_trigram=",
        "body_trigram=",
        "use_trigram=",
        "mutual_upper_trigram=",
        "mutual_lower_trigram=",
        "changed_use_trigram=",
        "body_use_relation=",
        "mutual_upper_relation=",
        "mutual_lower_relation=",
        "changed_use_relation=",
        "body_season_state=",
    )
    unknown = [name for name in features if not name.startswith(expected_prefixes)]
    if unknown:
        raise ValueError("Meihua feature schema 含未知欄位：" + "、".join(sorted(unknown)))
