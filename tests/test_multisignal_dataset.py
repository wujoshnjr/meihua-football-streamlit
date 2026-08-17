from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from jarvis.research.dataset import HistoricalFixture, build_multisignal_dataset_row
from qimen.features import PrematchFeatureSnapshot, TeamFormSnapshot


TZ = ZoneInfo("Asia/Taipei")


def _football_snapshot() -> PrematchFeatureSnapshot:
    cutoff = datetime(2026, 1, 10, 14, tzinfo=TZ)
    home = TeamFormSnapshot(
        team_id="home-id",
        matches=20,
        effective_matches=12.0,
        goals_for_per_match=1.5,
        goals_against_per_match=0.9,
        xg_for_per_match=1.6,
        xg_against_per_match=1.0,
        xg_weight_coverage=1.0,
        selected_match_ids=("h1", "h2"),
    )
    away = TeamFormSnapshot(
        team_id="away-id",
        matches=20,
        effective_matches=11.0,
        goals_for_per_match=1.2,
        goals_against_per_match=1.1,
        xg_for_per_match=1.25,
        xg_against_per_match=1.15,
        xg_weight_coverage=1.0,
        selected_match_ids=("a1", "a2"),
    )
    return PrematchFeatureSnapshot(
        schema_version="fixture-football-v1",
        git_commit="test",
        competition="Test League",
        cutoff_at=cutoff,
        half_life_days=180.0,
        maximum_team_matches=20,
        league_lookback_days=730,
        home=home,
        away=away,
        league_home_goals_per_match=1.45,
        league_away_goals_per_match=1.15,
        league_matches=200,
        source_match_ids=("h1", "h2", "a1", "a2"),
        source_payload_sha256="a" * 64,
        warnings=(),
        fingerprint_sha256="b" * 64,
    )


def _fixture(schedule_available_at: datetime | None = None) -> HistoricalFixture:
    event_at = datetime(2026, 1, 10, 20, tzinfo=TZ)
    return HistoricalFixture(
        match_id="fixture-1",
        competition="Test League",
        event_at=event_at,
        timezone_name="Asia/Taipei",
        home_team_id="home-id",
        away_team_id="away-id",
        schedule_available_at=schedule_available_at or event_at - timedelta(days=1),
        venue_mode="TRUE_HOME",
        dataset_role="TRAIN",
        evaluation_block="2026-W02",
        experiment_id="exp-v8",
        actual_home_goals=1,
        actual_away_goals=0,
    )


def test_builder_is_deterministic_and_contains_both_signal_families():
    football = _football_snapshot()
    first = build_multisignal_dataset_row(_fixture(), football)
    second = build_multisignal_dataset_row(_fixture(), football)
    assert first.fingerprint_sha256 == second.fingerprint_sha256
    assert first.record.fingerprint_sha256 == second.record.fingerprint_sha256
    assert first.record.cutoff == football.cutoff_at
    assert first.qimen_numeric_features
    assert first.meihua_numeric_features
    assert first.record.qimen_snapshot.available_at < first.record.cutoff
    assert first.record.meihua_snapshot.available_at < first.record.cutoff
    assert first.football_model_input["data_as_of"] == football.cutoff_at.isoformat()


def test_builder_rejects_schedule_known_after_cutoff():
    football = _football_snapshot()
    with pytest.raises(ValueError, match="schedule 在 cutoff 後才可得"):
        build_multisignal_dataset_row(
            _fixture(schedule_available_at=football.cutoff_at + timedelta(minutes=1)),
            football,
        )


def test_builder_rejects_team_identity_mismatch():
    football = _football_snapshot()
    fixture = _fixture()
    fixture = HistoricalFixture(**{**fixture.__dict__, "home_team_id": "wrong-home"})
    with pytest.raises(ValueError, match="home_team_id"):
        build_multisignal_dataset_row(fixture, football)
