"""Deterministic Meihua Yishu research features for JARVIS.

This package is research-only. It never emits football probabilities or fixed scores.
"""

from .engine import MEIHUA_ENGINE_VERSION, MeihuaSnapshot, build_meihua_snapshot, build_meihua_snapshot_from_numbers
from .outcome_features import MEIHUA_OUTCOME_DESIGN_VERSION, meihua_outcome_numeric_features

__all__ = [
    "MEIHUA_ENGINE_VERSION",
    "MEIHUA_OUTCOME_DESIGN_VERSION",
    "MeihuaSnapshot",
    "build_meihua_snapshot",
    "build_meihua_snapshot_from_numbers",
    "meihua_outcome_numeric_features",
]
