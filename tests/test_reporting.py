from __future__ import annotations

import hashlib
import json

from qimen.engine import cast_qimen
from qimen.football import interpret_football
from qimen.interpretation import build_interpretation_guide
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
    guide = build_interpretation_guide(
        board,
        question="本場雙方最可能呈現哪些可觀察的攻守結構？",
        match=match,
        locked_at=calendar_context.local_datetime,
    )
    bundle = build_bundle(match, board, reading, guide=guide, locked_at=calendar_context.local_datetime)
    assert bundle["interpretation_guide"]["focus_id"] == "whole_match"
    assert bundle["boundaries"]["question_locked_before_cast"] is True
    fingerprint = bundle.pop("fingerprint_sha256")
    assert hashlib.sha256(canonical_json(bundle).encode("utf-8")).hexdigest() == fingerprint
    json.dumps(bundle, ensure_ascii=False)

    report = render_markdown(match, board, reading, guide=guide)
    assert "奇門遁甲足球賽前研究報告" in report
    assert "九宮盤" in report
    assert "完整足球義" in report
    assert "可觀察訊號" in report
    assert "反證條件" in report
    assert "起局／解盤鎖定" in report
    assert "十層判讀順序" in report
    assert "不是勝率" in report
