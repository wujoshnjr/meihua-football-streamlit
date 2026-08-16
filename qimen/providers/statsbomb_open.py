from __future__ import annotations

from datetime import date, datetime, time
import json
from pathlib import Path
from typing import Any

from ..calendar import aware_local_datetime
from ..integrity import sha256_file
from .base import NormalizedMatch


class StatsBombOpenDataProvider:
    """Read a local snapshot of Hudl StatsBomb Open Data without network calls.

    StatsBomb match files provide local date/time values but not a reliable IANA
    timezone for every competition. Callers must therefore supply the competition
    timezone explicitly; the adapter never guesses it from a country or UTC offset.
    """

    provider_name = "statsbomb-open-data"
    attribution = "Data source: Hudl StatsBomb Open Data"
    upstream_url = "https://github.com/hudl/open-data"

    def __init__(self, root: str | Path):
        self.root = Path(root)

    def competitions_path(self) -> Path:
        return self.root / "data" / "competitions.json"

    def matches_path(self, competition_id: int | str, season_id: int | str) -> Path:
        return self.root / "data" / "matches" / str(competition_id) / f"{season_id}.json"

    def events_path(self, match_id: int | str) -> Path:
        return self.root / "data" / "events" / f"{match_id}.json"

    def lineups_path(self, match_id: int | str) -> Path:
        return self.root / "data" / "lineups" / f"{match_id}.json"

    @staticmethod
    def _read_json(path: Path) -> Any:
        try:
            with path.open(encoding="utf-8") as handle:
                return json.load(handle)
        except FileNotFoundError as exc:
            raise FileNotFoundError(f"找不到 StatsBomb Open Data 快照：{path}") from exc
        except json.JSONDecodeError as exc:
            raise ValueError(f"StatsBomb Open Data JSON 無效：{path}") from exc

    def load_competitions(self) -> list[dict[str, Any]]:
        payload = self._read_json(self.competitions_path())
        if not isinstance(payload, list):
            raise ValueError("competitions.json 根節點必須為陣列")
        return payload

    def load_matches(
        self,
        competition_id: int | str,
        season_id: int | str,
        *,
        timezone_name: str,
    ) -> list[NormalizedMatch]:
        if not timezone_name.strip():
            raise ValueError("必須明示賽事 IANA 時區，不可由資料集猜測")
        path = self.matches_path(competition_id, season_id)
        payload = self._read_json(path)
        if not isinstance(payload, list):
            raise ValueError("StatsBomb matches JSON 根節點必須為陣列")
        snapshot_hash = sha256_file(path)
        normalized: list[NormalizedMatch] = []
        for index, row in enumerate(payload, 1):
            try:
                match_date = date.fromisoformat(str(row["match_date"]))
                kickoff_time = time.fromisoformat(str(row["kick_off"]))
                kickoff_at = aware_local_datetime(
                    datetime.combine(match_date, kickoff_time),
                    timezone_name.strip(),
                )
                competition = row["competition"]
                season = row["season"]
                home = row["home_team"]
                away = row["away_team"]
                match_id = str(row["match_id"])
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(f"StatsBomb matches JSON 第 {index} 筆缺少必要欄位") from exc
            normalized.append(NormalizedMatch(
                provider=self.provider_name,
                provider_match_id=match_id,
                competition_id=str(competition.get("competition_id", competition_id)),
                competition_name=str(competition.get("competition_name", "")),
                season_id=str(season.get("season_id", season_id)),
                season_name=str(season.get("season_name", "")),
                kickoff_at=kickoff_at,
                timezone_name=timezone_name.strip(),
                home_team_id=str(home["home_team_id"]),
                home_team_name=str(home["home_team_name"]),
                away_team_id=str(away["away_team_id"]),
                away_team_name=str(away["away_team_name"]),
                home_score=int(row["home_score"]) if row.get("home_score") is not None else None,
                away_score=int(row["away_score"]) if row.get("away_score") is not None else None,
                status=str(row.get("match_status", "unknown")),
                source_path=str(path),
                source_snapshot_sha256=snapshot_hash,
            ))
        return normalized
