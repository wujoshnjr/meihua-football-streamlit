from __future__ import annotations

from datetime import datetime

from qimen.calendar import SEXAGENARY, build_calendar_context, sexagenary_index, xun_for
from qimen.engine import determine_dun, determine_ju, determine_yuan, deploy_earth_plate


# 《元靈經》日奇門正文把六十日按每三日一組，依次規定某宮「起休」。
# 宮序明文為 1,2,3,4,6,7,8,9，循環至六十日止；中五不作起休宮。
_RI_QIMEN_REST_START_SEQUENCE: tuple[int, ...] = (
    1, 2, 3, 4, 6, 7, 8, 9,
    1, 2, 3, 4, 6, 7, 8, 9,
    1, 2, 3, 4,
)


def rest_door_start_palace(day_ganzhi: str) -> int:
    """Return the palace explicitly assigned as 日奇門「起休」 for a sexagenary day.

    This is a direct machine-readable reconstruction of the 60-day table.  It
    does *not* by itself claim to finish the full Ri-Qimen heaven plate.
    """

    index = sexagenary_index(day_ganzhi)
    return _RI_QIMEN_REST_START_SEQUENCE[index // 3]


def riqimen_60_day_table() -> list[dict[str, object]]:
    return [
        {
            "day_index": index + 1,
            "day_ganzhi": ganzhi,
            "rest_door_start_palace": rest_door_start_palace(ganzhi),
        }
        for index, ganzhi in enumerate(SEXAGENARY)
    ]


def build_riqimen_base(event_at: datetime, timezone_name: str) -> dict[str, object]:
    """Build only the Ri-Qimen facts that are currently source-reconstructable.

    The text explicitly says to use the current solar-term three-yuan Ju as the
    earth plate and gives the 60-day 起休 table.  The later 「穿宮數去」 step is
    intentionally left unresolved rather than copied from the Shijia engine by
    analogy.
    """

    calendar = build_calendar_context(event_at, timezone_name)
    dun = determine_dun(calendar.solar_term)
    yuan, fu_head_day = determine_yuan(calendar.day_ganzhi)
    ju = determine_ju(calendar.solar_term, yuan)
    earth_plate = deploy_earth_plate(ju, dun)
    day_xun, day_instrument, _, day_offset = xun_for(calendar.day_ganzhi)

    return {
        "kind": "YUANLING_RI_QIMEN_BASE_V1",
        "status": "PARTIAL_SOURCE_GROUNDED__HEAVEN_PLATE_PENDING",
        "event": {
            "local_datetime": calendar.local_datetime.isoformat(),
            "timezone": timezone_name,
            "tzdb_version": calendar.tzdb_version,
        },
        "calendar": {
            "solar_term": calendar.solar_term,
            "solar_term_at": calendar.solar_term_at.isoformat(),
            "day_ganzhi": calendar.day_ganzhi,
            "hour_ganzhi": calendar.hour_ganzhi,
            "dun": dun,
            "yuan": yuan,
            "ju": ju,
            "ju_label": f"{dun}{ju}局",
        },
        "source_reconstructed": {
            "earth_plate": {str(palace): stem for palace, stem in sorted(earth_plate.items())},
            "rest_door_start_palace": rest_door_start_palace(calendar.day_ganzhi),
            "day_xun": day_xun,
            "day_xun_head_instrument": day_instrument,
            "day_xun_offset": day_offset,
            "fu_head_day": fu_head_day,
        },
        "unresolved": [
            {
                "id": "RIQIMEN_CHUANGONG_COUNTING",
                "text": "值符之上星加本日干穿宮數去",
                "status": "REQUIRES_SOURCE_RECONSTRUCTION",
                "rule": "Do not substitute the Shijia rotating-plate placement algorithm by analogy.",
            },
            {
                "id": "RIQIMEN_STAR_IDENTITY",
                "status": "REQUIRES_SOURCE_RECONSTRUCTION",
                "rule": "Do not assume the Ri-Qimen moving-star layer equals the Yanshu numeric-star layer.",
            },
        ],
        "authority": "YUANLING_SOURCE_RECONSTRUCTION",
        "boundary": (
            "此物件是日奇門 source-grounded base，不是完整日奇門天盤；"
            "未解的穿宮與星門步驟不得用現有時家盤靜默補足。"
        ),
    }
