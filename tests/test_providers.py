from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from qimen.providers import StatsBombOpenDataProvider


def test_statsbomb_local_snapshot_requires_explicit_timezone_and_hashes_source():
    with TemporaryDirectory() as temporary_directory:
        root = Path(temporary_directory)
        matches_directory = root / "data" / "matches" / "43"
        matches_directory.mkdir(parents=True)
        path = matches_directory / "3.json"
        path.write_text(json.dumps([{
            "match_id": 123,
            "match_date": "2026-01-10",
            "kick_off": "20:00:00.000",
            "competition": {"competition_id": 43, "competition_name": "Test Cup"},
            "season": {"season_id": 3, "season_name": "2026"},
            "home_team": {"home_team_id": 1, "home_team_name": "Home"},
            "away_team": {"away_team_id": 2, "away_team_name": "Away"},
            "home_score": 2,
            "away_score": 1,
            "match_status": "available"
        }]), encoding="utf-8")

        provider = StatsBombOpenDataProvider(root)
        matches = provider.load_matches(43, 3, timezone_name="Asia/Taipei")
        assert len(matches) == 1
        assert matches[0].kickoff_at.isoformat().endswith("+08:00")
        assert matches[0].provider_match_id == "123"
        assert len(matches[0].source_snapshot_sha256) == 64
        assert provider.events_path(123).name == "123.json"
        assert provider.lineups_path(123).name == "123.json"
