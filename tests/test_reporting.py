from __future__ import annotations

import hashlib
import json

from qimen.engine import cast_qimen
from qimen.football import interpret_football
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
    bundle = build_bundle(match, board, reading)
    fingerprint = bundle.pop("fingerprint_sha256")
    assert hashlib.sha256(canonical_json(bundle).encode("utf-8")).hexdigest() == fingerprint
    json.dumps(bundle, ensure_ascii=False)

    report = render_markdown(match, board, reading)
    assert "奇門遁甲足球賽前研究報告" in report
    assert "九宮盤" in report
    assert "不是勝率" in report
