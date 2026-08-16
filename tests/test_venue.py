import pytest

from qimen.venue import resolve_venue_baseline


def test_true_home_uses_registered_league_split():
    baseline = resolve_venue_baseline(
        venue_mode="TRUE_HOME",
        league_home_goals_per_match=1.50,
        league_away_goals_per_match=1.20,
        source="training-window:abc",
    )

    assert baseline.venue_mode == "TRUE_HOME"
    assert baseline.home_goals_per_match == pytest.approx(1.50)
    assert baseline.away_goals_per_match == pytest.approx(1.20)


def test_neutral_requires_explicit_neutral_estimate():
    with pytest.raises(ValueError, match="中立場必須提供"):
        resolve_venue_baseline(
            venue_mode="NEUTRAL",
            league_home_goals_per_match=1.50,
            league_away_goals_per_match=1.20,
            source="training-window:abc",
        )


def test_neutral_uses_only_registered_neutral_means():
    baseline = resolve_venue_baseline(
        venue_mode="NEUTRAL",
        league_home_goals_per_match=1.50,
        league_away_goals_per_match=1.20,
        neutral_home_goals_per_match=1.31,
        neutral_away_goals_per_match=1.29,
        source="neutral-training-window:def",
    )

    assert baseline.home_goals_per_match == pytest.approx(1.31)
    assert baseline.away_goals_per_match == pytest.approx(1.29)
    assert baseline.source == "neutral-training-window:def"
