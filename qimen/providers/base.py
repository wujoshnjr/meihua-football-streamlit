from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class NormalizedMatch:
    provider: str
    provider_match_id: str
    competition_id: str
    competition_name: str
    season_id: str
    season_name: str
    kickoff_at: datetime
    timezone_name: str
    home_team_id: str
    home_team_name: str
    away_team_id: str
    away_team_name: str
    home_score: int | None
    away_score: int | None
    status: str
    source_path: str
    source_snapshot_sha256: str

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["kickoff_at"] = self.kickoff_at.isoformat()
        return payload
