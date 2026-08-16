from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from math import isfinite
from typing import Any, Iterable

from .integrity import sha256_payload
from .prediction import PrematchModelInput, TeamForm
from .runtime import detect_git_commit


FEATURE_SNAPSHOT_VERSION = "jarvis-time-decayed-team-form-v1.0.0"


def _valid_hash(value: str) -> bool:
    return len(value) == 64 and all(character in "0123456789abcdef" for character in value)


@dataclass(frozen=True)
class HistoricalMatch:
    match_id: str
    competition: str
    event_at: datetime
    home_team_id: str
    away_team_id: str
    home_goals: int
    away_goals: int
    source_payload_sha256: str
    home_xg: float | None = None
    away_xg: float | None = None
    available_at: datetime | None = None

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.match_id.strip() or not self.competition.strip():
            errors.append("歷史比賽必須有 match_id 與 competition")
        if self.event_at.tzinfo is None:
            errors.append(f"{self.match_id} 的 event_at 必須含時區")
        if self.available_at is None or self.available_at.tzinfo is None:
            errors.append(f"{self.match_id} 的 available_at 必須含時區")
        elif self.available_at < self.event_at:
            errors.append(f"{self.match_id} 的 available_at 不可早於開賽")
        if not self.home_team_id.strip() or not self.away_team_id.strip():
            errors.append(f"{self.match_id} 的隊伍 ID 不可空白")
        if self.home_team_id.strip() == self.away_team_id.strip():
            errors.append(f"{self.match_id} 的主客隊不可相同")
        for label, value in (("home_goals", self.home_goals), ("away_goals", self.away_goals)):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                errors.append(f"{self.match_id} 的 {label} 必須為非負整數")
        for label, value in (("home_xg", self.home_xg), ("away_xg", self.away_xg)):
            if value is not None and (not isfinite(value) or value < 0):
                errors.append(f"{self.match_id} 的 {label} 必須為有限非負數")
        if not _valid_hash(self.source_payload_sha256):
            errors.append(f"{self.match_id} 的 source_payload_sha256 無效")
        return errors

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["event_at"] = self.event_at.isoformat()
        payload["available_at"] = self.available_at.isoformat() if self.available_at else None
        return payload


@dataclass(frozen=True)
class TeamFormSnapshot:
    team_id: str
    matches: int
    effective_matches: float
    goals_for_per_match: float
    goals_against_per_match: float
    xg_for_per_match: float | None
    xg_against_per_match: float | None
    xg_weight_coverage: float
    selected_match_ids: tuple[str, ...]

    def to_team_form(self) -> TeamForm:
        return TeamForm(
            matches=self.matches,
            goals_for_per_match=self.goals_for_per_match,
            goals_against_per_match=self.goals_against_per_match,
            xg_for_per_match=self.xg_for_per_match,
            xg_against_per_match=self.xg_against_per_match,
            effective_matches=self.effective_matches,
        )


@dataclass(frozen=True)
class PrematchFeatureSnapshot:
    schema_version: str
    git_commit: str
    competition: str
    cutoff_at: datetime
    half_life_days: float
    maximum_team_matches: int
    league_lookback_days: int
    home: TeamFormSnapshot
    away: TeamFormSnapshot
    league_home_goals_per_match: float
    league_away_goals_per_match: float
    league_matches: int
    source_match_ids: tuple[str, ...]
    source_payload_sha256: str
    warnings: tuple[str, ...]
    fingerprint_sha256: str

    @property
    def data_source(self) -> str:
        return f"team-form-snapshot:{self.fingerprint_sha256}"

    def to_model_input(self, **overrides: Any) -> PrematchModelInput:
        values: dict[str, Any] = {
            "home": self.home.to_team_form(),
            "away": self.away.to_team_form(),
            "league_home_goals_per_match": self.league_home_goals_per_match,
            "league_away_goals_per_match": self.league_away_goals_per_match,
            "data_as_of": self.cutoff_at,
            "data_source": self.data_source,
        }
        values.update(overrides)
        return PrematchModelInput(**values)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["cutoff_at"] = self.cutoff_at.isoformat()
        payload["data_source"] = self.data_source
        return payload


def _team_snapshot(
    rows: list[HistoricalMatch],
    team_id: str,
    cutoff_at: datetime,
    *,
    half_life_days: float,
    maximum_matches: int,
    minimum_xg_coverage: float,
) -> TeamFormSnapshot:
    selected = [
        row
        for row in sorted(rows, key=lambda item: (item.event_at, item.match_id), reverse=True)
        if team_id in {row.home_team_id, row.away_team_id}
    ][:maximum_matches]
    if not selected:
        raise ValueError(f"{team_id} 在 cutoff 前沒有可用歷史比賽")

    weights = [
        0.5 ** ((cutoff_at - row.event_at).total_seconds() / 86400 / half_life_days)
        for row in selected
    ]
    total_weight = sum(weights)
    goals_for: list[float] = []
    goals_against: list[float] = []
    xg_for: list[float | None] = []
    xg_against: list[float | None] = []
    for row in selected:
        is_home = row.home_team_id == team_id
        goals_for.append(float(row.home_goals if is_home else row.away_goals))
        goals_against.append(float(row.away_goals if is_home else row.home_goals))
        xg_for.append(row.home_xg if is_home else row.away_xg)
        xg_against.append(row.away_xg if is_home else row.home_xg)

    available_xg = [
        index
        for index, (for_value, against_value) in enumerate(zip(xg_for, xg_against))
        if for_value is not None and against_value is not None
    ]
    xg_weight = sum(weights[index] for index in available_xg)
    xg_coverage = xg_weight / total_weight
    use_xg = xg_coverage >= minimum_xg_coverage and xg_weight > 0
    return TeamFormSnapshot(
        team_id=team_id,
        matches=len(selected),
        effective_matches=total_weight,
        goals_for_per_match=sum(weight * value for weight, value in zip(weights, goals_for)) / total_weight,
        goals_against_per_match=sum(weight * value for weight, value in zip(weights, goals_against)) / total_weight,
        xg_for_per_match=(
            sum(weights[index] * float(xg_for[index]) for index in available_xg) / xg_weight
            if use_xg
            else None
        ),
        xg_against_per_match=(
            sum(weights[index] * float(xg_against[index]) for index in available_xg) / xg_weight
            if use_xg
            else None
        ),
        xg_weight_coverage=xg_coverage,
        selected_match_ids=tuple(row.match_id for row in selected),
    )


def build_prematch_feature_snapshot(
    matches: Iterable[HistoricalMatch],
    *,
    competition: str,
    home_team_id: str,
    away_team_id: str,
    cutoff_at: datetime,
    half_life_days: float = 180.0,
    maximum_team_matches: int = 20,
    league_lookback_days: int = 730,
    minimum_league_matches: int = 50,
    minimum_xg_coverage: float = 0.80,
) -> PrematchFeatureSnapshot:
    """Build symmetric, time-decayed features using only matches before cutoff."""

    if cutoff_at.tzinfo is None:
        raise ValueError("cutoff_at 必須含時區")
    if not competition.strip() or not home_team_id.strip() or not away_team_id.strip():
        raise ValueError("competition 與主客隊 ID 不可空白")
    if home_team_id.strip() == away_team_id.strip():
        raise ValueError("主客隊 ID 不可相同")
    if not isfinite(half_life_days) or half_life_days <= 0:
        raise ValueError("half_life_days 必須為有限正數")
    if maximum_team_matches < 5:
        raise ValueError("maximum_team_matches 至少為 5")
    if league_lookback_days < 30 or minimum_league_matches < 1:
        raise ValueError("聯盟回看天數／最低場數無效")
    if not 0 <= minimum_xg_coverage <= 1:
        raise ValueError("minimum_xg_coverage 必須介於 0 與 1")

    all_rows = list(matches)
    errors = [error for row in all_rows for error in row.validate()]
    if errors:
        raise ValueError("；".join(errors))
    if len({row.match_id.strip() for row in all_rows}) != len(all_rows):
        raise ValueError("歷史比賽含重複 match_id")
    eligible = [
        row
        for row in all_rows
        if row.competition == competition
        and row.event_at < cutoff_at
        and row.available_at is not None
        and row.available_at <= cutoff_at
    ]
    if not eligible:
        raise ValueError("cutoff 前沒有同聯賽歷史資料")

    league_start = cutoff_at - timedelta(days=league_lookback_days)
    league_rows = [row for row in eligible if row.event_at >= league_start]
    if len(league_rows) < minimum_league_matches:
        raise ValueError(f"聯盟基準至少需要 {minimum_league_matches} 場 cutoff 前比賽")
    league_weights = [
        0.5 ** ((cutoff_at - row.event_at).total_seconds() / 86400 / half_life_days)
        for row in league_rows
    ]
    league_weight = sum(league_weights)
    home = _team_snapshot(
        eligible,
        home_team_id,
        cutoff_at,
        half_life_days=half_life_days,
        maximum_matches=maximum_team_matches,
        minimum_xg_coverage=minimum_xg_coverage,
    )
    away = _team_snapshot(
        eligible,
        away_team_id,
        cutoff_at,
        half_life_days=half_life_days,
        maximum_matches=maximum_team_matches,
        minimum_xg_coverage=minimum_xg_coverage,
    )
    warnings: list[str] = []
    for label, snapshot in (("主隊", home), ("客隊", away)):
        if snapshot.matches < maximum_team_matches:
            warnings.append(f"{label}只有 {snapshot.matches} 場 cutoff 前同聯賽資料。")
        if snapshot.xg_for_per_match is None:
            warnings.append(f"{label} xG 有效權重覆蓋 {snapshot.xg_weight_coverage:.1%}，未達門檻。")

    source_ids = {
        *(row.match_id for row in league_rows),
        *home.selected_match_ids,
        *away.selected_match_ids,
    }
    source_rows = sorted(
        (row for row in eligible if row.match_id in source_ids),
        key=lambda item: (item.event_at, item.match_id),
    )
    source_payload = [row.to_dict() for row in source_rows]
    core = {
        "schema_version": FEATURE_SNAPSHOT_VERSION,
        "git_commit": detect_git_commit(),
        "competition": competition,
        "cutoff_at": cutoff_at.isoformat(),
        "half_life_days": half_life_days,
        "maximum_team_matches": maximum_team_matches,
        "league_lookback_days": league_lookback_days,
        "home": asdict(home),
        "away": asdict(away),
        "league_home_goals_per_match": sum(
            weight * row.home_goals for weight, row in zip(league_weights, league_rows)
        ) / league_weight,
        "league_away_goals_per_match": sum(
            weight * row.away_goals for weight, row in zip(league_weights, league_rows)
        ) / league_weight,
        "league_matches": len(league_rows),
        "source_match_ids": [row.match_id for row in source_rows],
        "source_payload_sha256": sha256_payload(source_payload),
        "warnings": warnings,
    }
    return PrematchFeatureSnapshot(
        schema_version=FEATURE_SNAPSHOT_VERSION,
        git_commit=core["git_commit"],
        competition=competition,
        cutoff_at=cutoff_at,
        half_life_days=half_life_days,
        maximum_team_matches=maximum_team_matches,
        league_lookback_days=league_lookback_days,
        home=home,
        away=away,
        league_home_goals_per_match=core["league_home_goals_per_match"],
        league_away_goals_per_match=core["league_away_goals_per_match"],
        league_matches=len(league_rows),
        source_match_ids=tuple(core["source_match_ids"]),
        source_payload_sha256=core["source_payload_sha256"],
        warnings=tuple(warnings),
        fingerprint_sha256=sha256_payload(core),
    )
