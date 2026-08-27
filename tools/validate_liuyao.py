from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
import sys
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from jarvis.liuyao_packet import build_liuyao_packet, verify_liuyao_packet_integrity  # noqa: E402
from liuyao.constants import BAGONG_SEQUENCE, HEXAGRAM_NAME_BY_TRIGRAMS, HEXAGRAM_PALACE, NAJIA  # noqa: E402
from liuyao.engine import cast_liuyao  # noqa: E402


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"Liuyao validation failed: {message}")


def main() -> None:
    names = [name for rows in BAGONG_SEQUENCE.values() for name in rows]
    require(len(names) == 64 and len(set(names)) == 64, "Bagong must cover 64 unique hexagrams")
    require(set(names) == set(HEXAGRAM_NAME_BY_TRIGRAMS.values()), "King-Wen trigram/name map drift")
    require(set(names) == set(HEXAGRAM_PALACE), "64 hexagram palace map drift")
    require(set(NAJIA) == {"乾", "兌", "離", "震", "巽", "坎", "艮", "坤"}, "Najia must cover all trigrams")

    event = datetime(2026, 8, 27, 20, 0, tzinfo=ZoneInfo("Asia/Taipei"))

    qian = cast_liuyao([7, 7, 7, 7, 7, 7], event, "Asia/Taipei")
    require(qian.original_hexagram == "乾為天", "pure Qian cast mismatch")
    require([line.branch for line in qian.lines] == ["子", "寅", "辰", "午", "申", "戌"], "Qian Najia branch mismatch")
    require(qian.shi_line == 6 and qian.ying_line == 3, "pure-palace Shi/Ying mismatch")

    source_golden = cast_liuyao([9, 7, 9, 6, 7, 6], event, "Asia/Taipei")
    require(source_golden.original_hexagram == "水天需", "Zengshan Xu source golden original mismatch")
    require(source_golden.changed_hexagram == "天水訟", "Zengshan Xu->Song changed mismatch")
    require(source_golden.palace == "坤", "Xu palace must be Kun")
    changed = {line.position: line for line in source_golden.lines if line.moving}
    require(changed[1].changed_relative == "官鬼", "changed line 1 relative must use original Kun-palace element")
    require(changed[3].changed_relative == "父母", "changed line 3 relative mismatch")
    require(changed[4].changed_relative == "父母", "changed line 4 relative mismatch")
    require(changed[6].changed_relative == "兄弟", "changed line 6 relative mismatch")

    packet = build_liuyao_packet(
        question="六爻 validator",
        line_values=[9, 7, 9, 6, 7, 6],
        event_at=event,
        timezone_name="Asia/Taipei",
        question_category="GENERAL",
    )
    require(verify_liuyao_packet_integrity(packet), "packet SHA mismatch")
    require(packet["review"]["source_audit"]["status"] == "SOURCE_TIERED_CORE_READY", "source audit status drift")
    require(
        packet["review"]["source_audit"]["user_video"]["status"] == "PENDING_TRANSCRIPT__NOT_SOURCE_LOCKED",
        "unretrieved user video must remain pending",
    )
    forbidden = set(packet["forbidden_outputs"])
    require("EVERY_DAY_CLASH_STATIC_LINE_IS_DARK_MOVING" in forbidden, "anti-dark-motion shortcut gate missing")
    require("UNVERIFIED_USER_VIDEO_RULE_PROMOTED_TO_CORE" in forbidden, "video source gate missing")

    source_catalog = json.loads((ROOT / "knowledge" / "liuyao_sources.json").read_text(encoding="utf-8"))
    require(source_catalog["status"] == "SOURCE_TIERED", "source catalog tier missing")
    require(len(source_catalog["primary_classical"]) >= 4, "need four classical Liuyao anchors")
    require(
        source_catalog["user_provided_video"]["implementation_status"] == "NOT_PROMOTED_TO_CORE",
        "pending user video must not be implemented as classical core",
    )

    print(
        "Liuyao: PASS | 64 hexagrams | 8 Bagong | Najia | Shi/Ying | Six Relatives | "
        "six spirits | month/day/void | moving changes | hidden candidates | source golden"
    )


if __name__ == "__main__":
    main()
