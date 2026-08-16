from __future__ import annotations

from datetime import timedelta

from qimen.protocol import EvidenceItem, MatchInput


def _match(calendar_context, evidence=None, refreshed=False):
    return MatchInput(
        match_id="TEST-001",
        home_team="Home",
        away_team="Away",
        competition="Test League",
        event_at=calendar_context.local_datetime,
        timezone_name=calendar_context.timezone_name,
        venue="Test Stadium",
        city="Taipei",
        evidence=evidence or [],
        both_teams_refreshed_after_material_update=refreshed,
    )


def test_freeze_at_is_six_hours(calendar_context):
    match = _match(calendar_context)
    assert match.freeze_at == match.event_at - timedelta(hours=6)
    assert match.validate() == []
    assert match.integrity_status()["overall"] == "PASS"


def test_postmatch_evidence_is_rejected(calendar_context):
    event = calendar_context.local_datetime
    item = EvidenceItem(
        "postmatch", "https://example.test", event + timedelta(minutes=1),
        event + timedelta(minutes=2), "other",
    )
    errors = _match(calendar_context, [item]).validate()
    assert sum("開賽後" in error for error in errors) == 2


def test_late_material_update_requires_symmetric_refresh(calendar_context):
    event = calendar_context.local_datetime
    item = EvidenceItem(
        "lineup", "https://example.test", event - timedelta(hours=1),
        event - timedelta(minutes=50), "official_lineup", material_update=True,
    )
    errors = _match(calendar_context, [item]).validate()
    assert any("同步刷新" in error for error in errors)
    assert _match(calendar_context, [item], refreshed=True).validate() == []


def test_late_nonmaterial_evidence_rejected(calendar_context):
    event = calendar_context.local_datetime
    item = EvidenceItem(
        "weather chatter", "https://example.test", event - timedelta(hours=1),
        event - timedelta(minutes=50), "weather", material_update=False,
    )
    assert any("不是重大" in error for error in _match(calendar_context, [item]).validate())


def test_source_must_be_published_before_it_is_retrieved(calendar_context):
    event = calendar_context.local_datetime
    item = EvidenceItem(
        "impossible chronology", "https://example.test/source",
        event - timedelta(hours=7), event - timedelta(hours=8), "team_form",
    )
    errors = _match(calendar_context, [item]).validate()
    assert any("發布時間不可晚於擷取時間" in error for error in errors)
    assert _match(calendar_context, [item]).integrity_status()["source_chronology"] == "FAIL"


def test_early_source_retrieved_after_freeze_is_not_silently_allowed(calendar_context):
    event = calendar_context.local_datetime
    item = EvidenceItem(
        "old page fetched late", "https://example.test/source",
        event - timedelta(hours=8), event - timedelta(hours=5), "team_form",
    )
    assert any("發布／擷取晚於 freeze_at" in error for error in _match(calendar_context, [item]).validate())
