from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from qimen.features import HistoricalMatch, build_prematch_feature_snapshot


HASH = "a" * 64


def _history():
    zone = ZoneInfo("UTC")
    cutoff = datetime(2026, 1, 1, tzinfo=zone)
    rows: list[HistoricalMatch] = []
    for index in range(60):
        team = "A" if index % 2 == 0 else "B"
        opponent = "C" if team == "A" else "D"
        event_at = cutoff - timedelta(days=60 - index)
        recent_high = team == "A" and index >= 50
        rows.append(HistoricalMatch(
            f"M-{index}", "League", event_at, team, opponent,
            5 if recent_high else 1, 1, HASH,
            home_xg=4.0 if recent_high else 1.0,
            away_xg=1.0,
            available_at=event_at + timedelta(hours=3),
        ))
    rows.append(HistoricalMatch(
        "FUTURE", "League", cutoff + timedelta(days=1), "A", "C",
        99, 0, HASH, home_xg=20.0, away_xg=0.0,
        available_at=cutoff + timedelta(days=1, hours=3),
    ))
    rows.append(HistoricalMatch(
        "NOT-YET-AVAILABLE", "League", cutoff - timedelta(hours=1), "A", "C",
        99, 0, HASH, home_xg=20.0, away_xg=0.0,
        available_at=cutoff + timedelta(hours=2),
    ))
    return cutoff, rows


def test_feature_snapshot_excludes_future_and_uses_one_symmetric_cutoff():
    cutoff, rows = _history()
    snapshot = build_prematch_feature_snapshot(
        rows,
        competition="League",
        home_team_id="A",
        away_team_id="B",
        cutoff_at=cutoff,
        half_life_days=30,
        maximum_team_matches=20,
        minimum_league_matches=50,
    )
    assert "FUTURE" not in snapshot.source_match_ids
    assert "NOT-YET-AVAILABLE" not in snapshot.source_match_ids
    assert snapshot.home.matches == snapshot.away.matches == 20
    assert snapshot.home.effective_matches < snapshot.home.matches
    assert snapshot.home.goals_for_per_match < 5
    assert snapshot.home.xg_weight_coverage == 1.0
    assert snapshot.cutoff_at == cutoff
    assert len(snapshot.fingerprint_sha256) == 64
    model_input = snapshot.to_model_input()
    assert model_input.home.effective_matches == snapshot.home.effective_matches
    assert model_input.data_source.startswith("team-form-snapshot:")


def test_shorter_half_life_gives_recent_form_more_influence():
    cutoff, rows = _history()
    short = build_prematch_feature_snapshot(
        rows,
        competition="League",
        home_team_id="A",
        away_team_id="B",
        cutoff_at=cutoff,
        half_life_days=10,
        maximum_team_matches=20,
        minimum_league_matches=50,
    )
    long = build_prematch_feature_snapshot(
        rows,
        competition="League",
        home_team_id="A",
        away_team_id="B",
        cutoff_at=cutoff,
        half_life_days=1000,
        maximum_team_matches=20,
        minimum_league_matches=50,
    )
    assert short.home.goals_for_per_match > long.home.goals_for_per_match
    assert short.home.effective_matches < long.home.effective_matches
