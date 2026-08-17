from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from math import isfinite
from typing import Iterable

from jarvis.provenance import sha256_payload
from jarvis.research.residual import ResidualLambdaObservation

from .strength import DynamicStrengthObservation


FOOTBALL_CONTEXT_VERSION = "jarvis-football-fixture-context-v0.1.0"
FOOTBALL_CONTEXT_FAMILY = "FOOTBALL_CONTEXT"
REST_CAP_DAYS = 14.0
CONGESTION_HOURS = 96.0


@dataclass(frozen=True)
class FixtureContextSnapshot:
    """Leakage-auditable schedule context known before one fixture.

    The snapshot deliberately stores schedule facts only. It does not assign a
    positive or negative football effect to short rest, congestion or workload;
    any predictive coefficient must be learned on TRAIN and selected on
    VALIDATION through the shared residual machinery.
    """

    schema_version: str
    cutoff_at: datetime
    home_team_id: str
    away_team_id: str
    home_previous_match_at: datetime | None
    away_previous_match_at: datetime | None
    home_rest_hours: float | None
    away_rest_hours: float | None
    home_matches_last_7d: int
    away_matches_last_7d: int
    home_matches_last_14d: int
    away_matches_last_14d: int
    selected_match_ids: tuple[str, ...]
    fingerprint_sha256: str

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["cutoff_at"] = self.cutoff_at.isoformat()
        payload["home_previous_match_at"] = (
            self.home_previous_match_at.isoformat() if self.home_previous_match_at else None
        )
        payload["away_previous_match_at"] = (
            self.away_previous_match_at.isoformat() if self.away_previous_match_at else None
        )
        return payload


def _team_match_times(
    rows: tuple[DynamicStrengthObservation, ...],
    team_id: str,
) -> tuple[datetime, ...]:
    return tuple(
        row.event_at
        for row in rows
        if row.home_team_id == team_id or row.away_team_id == team_id
    )


def _count_since(times: tuple[datetime, ...], cutoff_at: datetime, days: int) -> int:
    lower = cutoff_at - timedelta(days=days)
    return sum(lower <= event_at < cutoff_at for event_at in times)


def build_fixture_context_snapshot(
    observations: Iterable[DynamicStrengthObservation],
    *,
    cutoff_at: datetime,
    home_team_id: str,
    away_team_id: str,
) -> FixtureContextSnapshot:
    """Derive rest/congestion facts using only information available by cutoff.

    Historical rows are admitted only when the match itself predates the cutoff
    and the source row was available no later than the cutoff. This intentionally
    mirrors the dynamic-strength leakage boundary.
    """

    if cutoff_at.tzinfo is None:
        raise ValueError("cutoff_at 必須含時區")
    if not home_team_id.strip() or not away_team_id.strip():
        raise ValueError("home_team_id/away_team_id 不可空白")
    if home_team_id == away_team_id:
        raise ValueError("home_team_id/away_team_id 不可相同")

    all_rows = tuple(observations)
    errors = [error for row in all_rows for error in row.validate()]
    if errors:
        raise ValueError("；".join(errors))
    if len({row.match_id for row in all_rows}) != len(all_rows):
        raise ValueError("歷史資料含重複 match_id")

    selected = tuple(
        sorted(
            (
                row
                for row in all_rows
                if row.event_at < cutoff_at and row.available_at <= cutoff_at
            ),
            key=lambda row: (row.event_at, row.match_id),
        )
    )
    home_times = _team_match_times(selected, home_team_id)
    away_times = _team_match_times(selected, away_team_id)
    home_previous = home_times[-1] if home_times else None
    away_previous = away_times[-1] if away_times else None
    home_rest = (
        (cutoff_at - home_previous).total_seconds() / 3600.0
        if home_previous is not None
        else None
    )
    away_rest = (
        (cutoff_at - away_previous).total_seconds() / 3600.0
        if away_previous is not None
        else None
    )

    core = {
        "schema_version": FOOTBALL_CONTEXT_VERSION,
        "cutoff_at": cutoff_at.isoformat(),
        "home_team_id": home_team_id,
        "away_team_id": away_team_id,
        "home_previous_match_at": home_previous.isoformat() if home_previous else None,
        "away_previous_match_at": away_previous.isoformat() if away_previous else None,
        "home_rest_hours": home_rest,
        "away_rest_hours": away_rest,
        "home_matches_last_7d": _count_since(home_times, cutoff_at, 7),
        "away_matches_last_7d": _count_since(away_times, cutoff_at, 7),
        "home_matches_last_14d": _count_since(home_times, cutoff_at, 14),
        "away_matches_last_14d": _count_since(away_times, cutoff_at, 14),
        "selected_match_ids": tuple(row.match_id for row in selected),
    }
    return FixtureContextSnapshot(
        schema_version=FOOTBALL_CONTEXT_VERSION,
        cutoff_at=cutoff_at,
        home_team_id=home_team_id,
        away_team_id=away_team_id,
        home_previous_match_at=home_previous,
        away_previous_match_at=away_previous,
        home_rest_hours=home_rest,
        away_rest_hours=away_rest,
        home_matches_last_7d=core["home_matches_last_7d"],
        away_matches_last_7d=core["away_matches_last_7d"],
        home_matches_last_14d=core["home_matches_last_14d"],
        away_matches_last_14d=core["away_matches_last_14d"],
        selected_match_ids=core["selected_match_ids"],
        fingerprint_sha256=sha256_payload(core),
    )


def fixture_context_numeric_features(snapshot: FixtureContextSnapshot) -> dict[str, float]:
    """Encode schedule facts without assigning an outcome direction by hand."""

    home_known = snapshot.home_rest_hours is not None
    away_known = snapshot.away_rest_hours is not None
    home_rest_days = min((snapshot.home_rest_hours or 0.0) / 24.0, REST_CAP_DAYS)
    away_rest_days = min((snapshot.away_rest_hours or 0.0) / 24.0, REST_CAP_DAYS)
    both_known = home_known and away_known
    return {
        "home_rest_known": float(home_known),
        "away_rest_known": float(away_known),
        "both_rest_known": float(both_known),
        "home_rest_days_capped": float(home_rest_days),
        "away_rest_days_capped": float(away_rest_days),
        "rest_days_difference": float(home_rest_days - away_rest_days) if both_known else 0.0,
        "home_under_96h": float(home_known and snapshot.home_rest_hours < CONGESTION_HOURS),
        "away_under_96h": float(away_known and snapshot.away_rest_hours < CONGESTION_HOURS),
        "home_matches_last_7d": float(snapshot.home_matches_last_7d),
        "away_matches_last_7d": float(snapshot.away_matches_last_7d),
        "home_matches_last_14d": float(snapshot.home_matches_last_14d),
        "away_matches_last_14d": float(snapshot.away_matches_last_14d),
    }


def build_context_residual_observation(
    snapshot: FixtureContextSnapshot,
    *,
    match_id: str,
    event_at: datetime,
    baseline_home_lambda: float,
    baseline_away_lambda: float,
    actual_home_goals: int,
    actual_away_goals: int,
    dataset_role: str = "TRAIN",
) -> ResidualLambdaObservation:
    """Adapt one context snapshot to the shared no-intercept residual engine."""

    if event_at.tzinfo is None:
        raise ValueError("event_at 必須含時區")
    if snapshot.cutoff_at >= event_at:
        raise ValueError("fixture context cutoff 必須早於 event_at")
    for label, value in (
        ("baseline_home_lambda", baseline_home_lambda),
        ("baseline_away_lambda", baseline_away_lambda),
    ):
        if not isfinite(value) or value <= 0:
            raise ValueError(f"{label} 必須為有限正數")
    payload = {
        "snapshot": snapshot.to_dict(),
        "match_id": match_id,
        "event_at": event_at.isoformat(),
        "baseline_home_lambda": baseline_home_lambda,
        "baseline_away_lambda": baseline_away_lambda,
        "actual_home_goals": actual_home_goals,
        "actual_away_goals": actual_away_goals,
        "dataset_role": dataset_role,
    }
    return ResidualLambdaObservation(
        match_id=match_id,
        event_at=event_at,
        baseline_home_lambda=baseline_home_lambda,
        baseline_away_lambda=baseline_away_lambda,
        actual_home_goals=actual_home_goals,
        actual_away_goals=actual_away_goals,
        features=fixture_context_numeric_features(snapshot),
        feature_family=FOOTBALL_CONTEXT_FAMILY,
        feature_schema_version=FOOTBALL_CONTEXT_VERSION,
        payload_sha256=sha256_payload(payload),
        dataset_role=dataset_role,
    )
