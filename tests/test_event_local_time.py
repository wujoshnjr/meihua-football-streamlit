from datetime import datetime

import pytest

from jarvis.time import EventLocalTimeError, aware_event_local_datetime, inspect_local_civil_time


def test_dst_fall_back_requires_explicit_fold_when_strict():
    wall = datetime(2026, 11, 1, 1, 30)
    audit = inspect_local_civil_time(wall, "America/New_York")

    assert audit["status"] == "AMBIGUOUS"
    assert audit["ambiguous"] is True
    assert audit["nonexistent"] is False
    assert len(audit["candidates"]) == 2
    assert audit["candidates"][0]["utc_datetime"] != audit["candidates"][1]["utc_datetime"]

    with pytest.raises(EventLocalTimeError, match="重複時間"):
        aware_event_local_datetime(
            wall,
            "America/New_York",
            reject_ambiguous_without_explicit_fold=True,
        )

    first = aware_event_local_datetime(wall, "America/New_York", fold=0)
    second = aware_event_local_datetime(wall, "America/New_York", fold=1)
    assert first.utcoffset() != second.utcoffset()
    assert first.astimezone().timestamp() != second.astimezone().timestamp()


def test_dst_spring_forward_nonexistent_time_is_rejected():
    wall = datetime(2026, 3, 8, 2, 30)
    audit = inspect_local_civil_time(wall, "America/New_York")

    assert audit["status"] == "NONEXISTENT"
    assert audit["nonexistent"] is True
    with pytest.raises(EventLocalTimeError, match="不存在"):
        aware_event_local_datetime(wall, "America/New_York")


def test_normal_local_time_is_unambiguous():
    wall = datetime(2026, 6, 15, 20, 0, 12)
    audit = inspect_local_civil_time(wall, "America/New_York")
    assert audit["status"] == "UNAMBIGUOUS"
    assert audit["ambiguous"] is False
    assert audit["nonexistent"] is False
