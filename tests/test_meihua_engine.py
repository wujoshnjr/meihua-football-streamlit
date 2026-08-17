from datetime import datetime, timezone

from meihua.engine import build_meihua_snapshot_from_numbers
from meihua.outcome_features import meihua_outcome_numeric_features


def test_observation_plum_example_arithmetic_and_body_use():
    # 辰年十二月十七日申時：34 -> 兌，上加申9=43 -> 離，下；43 mod 6 -> 初爻。
    snapshot = build_meihua_snapshot_from_numbers(
        event_local_at=datetime(2000, 1, 1, tzinfo=timezone.utc),
        timezone_name="UTC",
        year_branch="辰",
        lunar_month=12,
        lunar_day=17,
        hour_branch="申",
    )
    assert snapshot.upper_trigram == "兌"
    assert snapshot.lower_trigram == "離"
    assert snapshot.moving_line == 1
    assert snapshot.body_trigram == "兌"
    assert snapshot.use_trigram == "離"
    assert snapshot.changed_lower_trigram == "艮"


def test_feature_encoder_is_raw_and_deterministic():
    snapshot = build_meihua_snapshot_from_numbers(
        event_local_at=datetime(2026, 6, 27, 19, 30, tzinfo=timezone.utc),
        timezone_name="UTC",
        year_branch="午",
        lunar_month=5,
        lunar_day=13,
        hour_branch="戌",
    )
    features = meihua_outcome_numeric_features(snapshot)
    assert features["moving_line"] == float(snapshot.moving_line)
    assert features[f"body_trigram={snapshot.body_trigram}"] == 1.0
    assert features[f"body_use_relation={snapshot.body_use_relation}"] == 1.0
    assert not any("home_win" in name or "goal_bonus" in name for name in features)
