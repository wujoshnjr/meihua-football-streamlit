"""Versioned, read-only football data provider adapters."""

from .base import NormalizedMatch
from .statsbomb_open import StatsBombOpenDataProvider

__all__ = ["NormalizedMatch", "StatsBombOpenDataProvider"]
