from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from qimen.calendar import xun_for  # noqa: E402
from qimen.engine import cast_qimen  # noqa: E402
from qimen.models import CalendarContext  # noqa: E402


FIXTURES = ROOT / "knowledge" / "qimen_source_golden_fixtures.json"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"Qimen source golden validation failed: {message}")


def _calendar(row: dict) -> CalendarContext:
    local = datetime.fromisoformat(row["local_time"])
    day_xun, _, day_void, _ = xun_for(row["day_ganzhi"])
    return CalendarContext(
        local_datetime=local,
        timezone_name=row["timezone"],
        solar_term=row["solar_term"],
        solar_term_at=local - timedelta(days=1),
        next_solar_term="NEXT_SYNTHETIC_TERM",
        next_solar_term_at=local + timedelta(days=14),
        year_ganzhi="SYNTHETIC",
        month_ganzhi="SYNTHETIC",
        day_ganzhi=row["day_ganzhi"],
        hour_ganzhi=row["hour_ganzhi"],
        day_xun=day_xun,
        day_void_branches=day_void,
        source="SOURCE_DERIVED_SYNTHETIC_CALENDAR_CONTEXT",
        tzdb_version="not-applicable",
    )


def main() -> None:
    payload = json.loads(FIXTURES.read_text(encoding="utf-8"))
    require(payload.get("status") == "SOURCE_DERIVED_METHOD_GOLDEN_READY", "fixture status drift")
    fixtures = payload.get("fixtures", [])
    require(len(fixtures) >= 4, "need at least four source-derived method fixtures")

    seen_dun: set[str] = set()
    seen_ju: set[int] = set()
    seen_source_patterns: set[str] = set()

    for fixture in fixtures:
        calendar = _calendar(fixture["calendar"])
        board = cast_qimen(calendar.local_datetime, calendar.timezone_name, calendar=calendar)
        expected = fixture["expected"]
        fid = fixture["id"]

        require(board.dun == expected["dun"], f"{fid}: dun {board.dun} != {expected['dun']}")
        require(board.yuan == expected["yuan"], f"{fid}: yuan {board.yuan} != {expected['yuan']}")
        require(board.ju == expected["ju"], f"{fid}: ju {board.ju} != {expected['ju']}")
        require(board.chief_star == expected["chief_star"], f"{fid}: chief star mismatch")
        require(board.chief_star_palace == expected["chief_star_palace"], f"{fid}: chief star palace mismatch")
        require(board.chief_door == expected["chief_door"], f"{fid}: chief door mismatch")
        require(board.chief_door_palace == expected["chief_door_palace"], f"{fid}: chief door palace mismatch")

        for number_text, stem in expected["earth"].items():
            number = int(number_text)
            require(board.palaces[number].earth_stem == stem, f"{fid}: palace {number} earth stem mismatch")

        for number_text, door in expected["doors"].items():
            number = int(number_text)
            require(board.palaces[number].door == door, f"{fid}: palace {number} door mismatch")

        for number_text, stars in expected["stars"].items():
            number = int(number_text)
            require(board.palaces[number].stars == stars, f"{fid}: palace {number} stars mismatch")

        for number_text, stems in expected["heaven_stems"].items():
            number = int(number_text)
            require(board.palaces[number].heaven_stems == stems, f"{fid}: palace {number} heaven stems mismatch")

        anchor = expected["source_anchor"]
        state = board.palaces[int(anchor["palace"])]
        require(state.door == anchor["door"], f"{fid}: source-anchor door mismatch")
        require(anchor["heaven_stem"] in state.heaven_stems, f"{fid}: source-anchor heaven stem mismatch")
        require(state.earth_stem == anchor["earth_stem"], f"{fid}: source-anchor earth stem mismatch")

        seen_dun.add(board.dun)
        seen_ju.add(board.ju)
        seen_source_patterns.add(anchor["pattern"])

    require(seen_dun == {"陽遁", "陰遁"}, "fixtures must cover both yang/yin dun")
    require({1, 4, 6, 9} <= seen_ju, "fixtures must preserve the four source-declared ju examples")
    require({"天遁", "地遁"} <= seen_source_patterns, "fixtures must cover both Tian Dun and Di Dun source anchors")

    print(
        "Qimen source golden validation passed: 4 source-derived classical method examples / "
        "yang+yin / ju 1,4,6,9 / full core earth-star-door-heaven-stem expectations / deity layer excluded by method boundary"
    )


if __name__ == "__main__":
    main()
