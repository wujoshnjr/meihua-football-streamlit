from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Iterable

from .football import FootballReading
from .reporting import canonical_json


@dataclass(frozen=True)
class LockedScenarios:
    match_id: str
    event_at: datetime
    locked_at: datetime
    scenario_titles: tuple[str, ...]
    fingerprint_sha256: str

    def to_dict(self):
        data = asdict(self)
        data["event_at"] = self.event_at.isoformat()
        data["locked_at"] = self.locked_at.isoformat()
        return data


def lock_scenarios(
    match_id: str,
    event_at: datetime,
    locked_at: datetime,
    reading: FootballReading,
) -> LockedScenarios:
    if event_at.tzinfo is None or locked_at.tzinfo is None:
        raise ValueError("event_at 與 locked_at 必須含時區")
    if locked_at >= event_at:
        raise ValueError("情境必須在開賽前鎖定")
    titles = tuple(item.title for item in reading.scenarios)
    import hashlib

    fingerprint = hashlib.sha256(canonical_json({
        "match_id": match_id,
        "event_at": event_at.isoformat(),
        "locked_at": locked_at.isoformat(),
        "scenario_titles": titles,
    }).encode("utf-8")).hexdigest()
    return LockedScenarios(match_id, event_at, locked_at, titles, fingerprint)


def evaluate_scenarios(
    locked: LockedScenarios,
    observed_tags: Iterable[str],
    *,
    top_k: int = 3,
) -> dict[str, object]:
    """Evaluate pre-locked qualitative scenarios without inventing probabilities."""

    observed = {tag.strip() for tag in observed_tags if tag.strip()}
    selected = locked.scenario_titles[:top_k]
    hits = tuple(title for title in selected if title in observed)
    return {
        "match_id": locked.match_id,
        "top_k": top_k,
        "selected": selected,
        "observed": tuple(sorted(observed)),
        "hits": hits,
        "precision_at_k": len(hits) / len(selected) if selected else 0.0,
        "note": "只評估賽前鎖定情境與人工標註事件的一致性，不回推出勝率。",
    }
