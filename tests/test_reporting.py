from __future__ import annotations

import hashlib
import json
from datetime import timedelta

from qimen.engine import cast_qimen
from qimen.evaluation import lock_prediction
from qimen.football import interpret_football
from qimen.interpretation import build_interpretation_guide
from qimen.prediction import PrematchModelInput, TeamForm, build_prediction
from qimen.protocol import MatchInput
from qimen.reporting import build_bundle, canonical_json, render_markdown


def test_bundle_fingerprint_and_markdown(calendar_context):
    match = MatchInput(
        "TEST-REPORT", "Home", "Away", "League",
        calendar_context.local_datetime, calendar_context.timezone_name,
        "Stadium", "Taipei",
    )
    board = cast_qimen(match.event_at, match.timezone_name, calendar=calendar_context)
    reading = interpret_football(board)
    locked_at = calendar_context.local_datetime - timedelta(hours=8)
    guide = build_interpretation_guide(
        board,
        question="本場雙方最可能呈現哪些可觀察的攻守結構？",
        match=match,
        locked_at=locked_at,
    )
    prediction = build_prediction(
        PrematchModelInput(
            home=TeamForm(10, 1.35, 1.35),
            away=TeamForm(10, 1.35, 1.35),
            data_as_of=calendar_context.local_datetime - timedelta(days=1),
            data_source="test-fixture",
        ),
        board,
        reading,
    )
    prediction_lock = lock_prediction(match.match_id, match.event_at, locked_at, prediction)
    bundle = build_bundle(
        match,
        board,
        reading,
        guide=guide,
        locked_at=locked_at,
        prediction=prediction,
        prediction_lock=prediction_lock,
    )
    assert bundle["schema_version"] == "qimen-football-bundle-v2.2.0"
    assert bundle["interpretation_guide"]["focus_id"] == "whole_match"
    assert bundle["boundaries"]["question_locked_before_cast"] is True
    assert bundle["boundaries"]["prediction_layer_present"] is True
    assert bundle["boundaries"]["probability_calibrated"] is False
    assert bundle["boundaries"]["qimen_changes_probability"] is False
    assert bundle["prediction_lock"]["fingerprint_sha256"] == prediction_lock.fingerprint_sha256
    fingerprint = bundle.pop("fingerprint_sha256")
    assert hashlib.sha256(canonical_json(bundle).encode("utf-8")).hexdigest() == fingerprint
    json.dumps(bundle, ensure_ascii=False)

    report = render_markdown(
        match,
        board,
        reading,
        guide=guide,
        prediction=prediction,
        prediction_lock=prediction_lock,
    )
    assert "奇門遁甲足球賽前研究報告" in report
    assert "九宮盤" in report
    assert "完整足球義" in report
    assert "可觀察訊號" in report
    assert "反證條件" in report
    assert "起局／解盤鎖定" in report
    assert "十層判讀順序" in report
    assert "不是勝率" in report
    assert "JARVIS 機率基準" in report
    assert "SHADOW_ONLY" in report
    assert "資料快照指紋" in report
    assert "Git commit" in report
