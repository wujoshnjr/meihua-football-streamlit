from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import isfinite
from typing import Any, Mapping, Sequence
from zoneinfo import ZoneInfo

from jarvis.provenance import sha256_payload
from jarvis.time import aware_event_local_datetime


STATSBOMB_OPEN_DATA_VERSION = "jarvis-statsbomb-open-data-v0.1.0"


@dataclass(frozen=True)
class StatsBombHistoricalMatch:
    """Normalized 90-minute historical row derived from StatsBomb Open Data."""

    match_id: str
    competition: str
    event_at: datetime
    available_at: datetime
    home_team_id: str
    away_team_id: str
    home_team_name: str
    away_team_name: str
    home_goals: int
    away_goals: int
    home_xg: float
    away_xg: float
    source_payload_sha256: str
    source_schema_version: str = STATSBOMB_OPEN_DATA_VERSION

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.match_id.strip() or not self.competition.strip():
            errors.append("StatsBomb row 必須有 match_id 與 competition")
        if self.event_at.tzinfo is None or self.available_at.tzinfo is None:
            errors.append(f"{self.match_id} 的 event_at/available_at 必須含時區")
        elif self.available_at < self.event_at:
            errors.append(f"{self.match_id} 的 available_at 不可早於 event_at")
        if not self.home_team_id.strip() or not self.away_team_id.strip():
            errors.append(f"{self.match_id} 的隊伍 ID 不可空白")
        if self.home_team_id == self.away_team_id:
            errors.append(f"{self.match_id} 的主客隊不可相同")
        for label, value in (("home_goals", self.home_goals), ("away_goals", self.away_goals)):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                errors.append(f"{self.match_id} 的 {label} 必須為非負整數")
        for label, value in (("home_xg", self.home_xg), ("away_xg", self.away_xg)):
            if not isfinite(value) or value < 0:
                errors.append(f"{self.match_id} 的 {label} 必須為有限非負數")
        if len(self.source_payload_sha256) != 64 or any(
            character not in "0123456789abcdef" for character in self.source_payload_sha256
        ):
            errors.append(f"{self.match_id} 的 source_payload_sha256 無效")
        return errors

    def to_historical_match(self):
        """Convert lazily to the legacy football feature row without a circular import."""

        from qimen.features import HistoricalMatch

        errors = self.validate()
        if errors:
            raise ValueError("；".join(errors))
        return HistoricalMatch(
            match_id=self.match_id,
            competition=self.competition,
            event_at=self.event_at,
            home_team_id=self.home_team_id,
            away_team_id=self.away_team_id,
            home_goals=self.home_goals,
            away_goals=self.away_goals,
            source_payload_sha256=self.source_payload_sha256,
            home_xg=self.home_xg,
            away_xg=self.away_xg,
            available_at=self.available_at,
        )


def _require_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"StatsBomb {label} 必須為 object")
    return value


def _require_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"StatsBomb {label} 必須為整數")
    return value


def _team_identity(match: Mapping[str, Any], side: str) -> tuple[str, str]:
    team = _require_mapping(match.get(f"{side}_team"), f"{side}_team")
    team_id = _require_int(team.get(f"{side}_team_id"), f"{side}_team_id")
    team_name = str(team.get(f"{side}_team_name", "")).strip()
    if not team_name:
        raise ValueError(f"StatsBomb {side}_team_name 不可空白")
    return str(team_id), team_name


def _event_team_id(event: Mapping[str, Any]) -> str | None:
    team = event.get("team")
    if not isinstance(team, Mapping):
        return None
    team_id = team.get("id")
    if isinstance(team_id, bool) or not isinstance(team_id, int):
        return None
    return str(team_id)


def _normal_time_xg(
    events: Sequence[Mapping[str, Any]],
    *,
    home_team_id: str,
    away_team_id: str,
) -> tuple[float, float]:
    home_xg = 0.0
    away_xg = 0.0
    for event in events:
        period = event.get("period")
        if period not in {1, 2}:
            continue
        event_type = event.get("type")
        if not isinstance(event_type, Mapping) or event_type.get("name") != "Shot":
            continue
        shot = event.get("shot")
        if not isinstance(shot, Mapping):
            continue
        xg = shot.get("statsbomb_xg")
        if not isinstance(xg, (int, float)) or isinstance(xg, bool) or not isfinite(float(xg)) or xg < 0:
            raise ValueError("StatsBomb Shot.statsbomb_xg 必須為有限非負數")
        team_id = _event_team_id(event)
        if team_id == home_team_id:
            home_xg += float(xg)
        elif team_id == away_team_id:
            away_xg += float(xg)
    return home_xg, away_xg


def parse_statsbomb_historical_match(
    match_payload: Mapping[str, Any],
    event_payload: Sequence[Mapping[str, Any]],
    *,
    timezone_name: str,
    available_at: datetime,
    normal_time_score_override: tuple[int, int] | None = None,
) -> StatsBombHistoricalMatch:
    """Normalize one StatsBomb match + events into a leakage-auditable 90-minute row.

    StatsBomb match metadata contains final scores. If any event uses period > 2,
    that final score may include extra time, so callers must supply an explicit
    registered 90-minute score override instead of letting this parser guess.
    Penalty shootout periods are never used for xG.
    """

    if available_at.tzinfo is None:
        raise ValueError("available_at 必須含時區")
    try:
        ZoneInfo(timezone_name)
    except Exception as exc:
        raise ValueError(f"無效 IANA 時區：{timezone_name}") from exc

    match_id = str(_require_int(match_payload.get("match_id"), "match_id"))
    competition_payload = _require_mapping(match_payload.get("competition"), "competition")
    competition = str(competition_payload.get("competition_name", "")).strip()
    if not competition:
        raise ValueError("StatsBomb competition_name 不可空白")
    match_date = str(match_payload.get("match_date", "")).strip()
    kick_off = str(match_payload.get("kick_off", "")).strip()
    if not match_date or not kick_off:
        raise ValueError("StatsBomb match_date/kick_off 不可空白")
    try:
        naive_event = datetime.fromisoformat(f"{match_date}T{kick_off}")
    except ValueError as exc:
        raise ValueError("StatsBomb match_date/kick_off 格式無法解析") from exc
    event_at = aware_event_local_datetime(naive_event, timezone_name)
    if available_at < event_at:
        raise ValueError("available_at 不可早於 event_at")

    home_team_id, home_team_name = _team_identity(match_payload, "home")
    away_team_id, away_team_name = _team_identity(match_payload, "away")
    if home_team_id == away_team_id:
        raise ValueError("StatsBomb 主客隊不可相同")

    periods = {
        period
        for event in event_payload
        if isinstance((period := event.get("period")), int) and not isinstance(period, bool)
    }
    has_extra_time = any(period > 2 for period in periods)
    if normal_time_score_override is None:
        if has_extra_time:
            raise ValueError("StatsBomb 比賽含加時/點球 period；必須提供 normal_time_score_override")
        home_goals = _require_int(match_payload.get("home_score"), "home_score")
        away_goals = _require_int(match_payload.get("away_score"), "away_score")
    else:
        if len(normal_time_score_override) != 2:
            raise ValueError("normal_time_score_override 必須是 (home, away)")
        home_goals, away_goals = normal_time_score_override
        for label, value in (("home", home_goals), ("away", away_goals)):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"normal_time_score_override {label} 必須為非負整數")

    events = tuple(_require_mapping(event, "event") for event in event_payload)
    home_xg, away_xg = _normal_time_xg(
        events,
        home_team_id=home_team_id,
        away_team_id=away_team_id,
    )
    source_hash = sha256_payload(
        {
            "source": "StatsBomb Open Data",
            "match": match_payload,
            "events": event_payload,
            "normal_time_score_override": normal_time_score_override,
        }
    )
    row = StatsBombHistoricalMatch(
        match_id=match_id,
        competition=competition,
        event_at=event_at,
        available_at=available_at,
        home_team_id=home_team_id,
        away_team_id=away_team_id,
        home_team_name=home_team_name,
        away_team_name=away_team_name,
        home_goals=home_goals,
        away_goals=away_goals,
        home_xg=home_xg,
        away_xg=away_xg,
        source_payload_sha256=source_hash,
    )
    errors = row.validate()
    if errors:
        raise ValueError("；".join(errors))
    return row
