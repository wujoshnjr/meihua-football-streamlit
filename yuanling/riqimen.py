from __future__ import annotations

from datetime import datetime

from qimen.calendar import SEXAGENARY, build_calendar_context, sexagenary_index, xun_for
from qimen.constants import PALACE_RING, PALACES
from qimen.engine import determine_dun, determine_ju, determine_yuan, deploy_earth_plate


_RI_QIMEN_REST_START_SEQUENCE = (
    1, 2, 3, 4, 6, 7, 8, 9,
    1, 2, 3, 4, 6, 7, 8, 9,
    1, 2, 3, 4,
)

_QIMEN_STAR_BY_NUMERIC_HOME: dict[int, str] = {
    1: "天蓬",
    2: "天芮",
    3: "天沖",
    4: "天輔",
    5: "天禽",
    6: "天心",
    7: "天柱",
    8: "天任",
    9: "天英",
}

_FORWARD_DOOR_ORDER = (
    "休門",
    "生門",
    "傷門",
    "杜門",
    "景門",
    "死門",
    "驚門",
    "開門",
)


def _advance_numeric_palace(start: int, steps: int, direction: int = 1) -> int:
    if start not in range(1, 10):
        raise ValueError(f"九宮必須為1..9：{start}")
    if direction not in (-1, 1):
        raise ValueError(f"direction 必須為1或-1：{direction}")
    return ((start - 1 + direction * steps) % 9) + 1


def _raw_stem_palace(earth_plate: dict[int, str], stem: str) -> int:
    for palace, value in earth_plate.items():
        if value == stem:
            return palace
    raise ValueError(f"地盤找不到天干：{stem}")


def _dun_direction(dun: str) -> int:
    if dun == "陽遁":
        return 1
    if dun == "陰遁":
        return -1
    raise ValueError(f"遁法必須為陽遁或陰遁：{dun}")


def _steps_between(start: int, target: int, direction: int) -> int:
    # direction is its own modular inverse because it is ±1.
    return ((target - start) * direction) % 9


def rest_door_start_palace(day_ganzhi: str) -> int:
    """Return the 60-day Ri-Qimen 休門 anchor transmitted in Yuanling vol. 1."""

    index = sexagenary_index(day_ganzhi)
    return _RI_QIMEN_REST_START_SEQUENCE[index // 3]


def riqimen_60_day_table() -> list[dict[str, object]]:
    return [
        {
            "day_index": index + 1,
            "day_ganzhi": day_ganzhi,
            "three_day_group": index // 3,
            "rest_door_start_palace": rest_door_start_palace(day_ganzhi),
        }
        for index, day_ganzhi in enumerate(SEXAGENARY)
    ]


def chuangong_star_plate(
    chief_origin_palace: int,
    chief_target_palace: int,
) -> dict[int, str]:
    """Fly the nine Qimen stars through numeric palaces, center included.

    Yuanling says 「值符之上星加本日干穿宮數去」 and then 「星門皆順」.
    The related day-Qimen examples in Qimen Dunjia Tongzong make the traversal
    concrete: e.g. a star at 艮八 is followed at 離九, then 坎一, 坤二 ...
    Thus "穿宮" is represented here as numeric 1..9 flight with wraparound,
    not the eight-palace rotating ring used by the production Shijia engine.
    """

    if chief_origin_palace not in _QIMEN_STAR_BY_NUMERIC_HOME:
        raise ValueError(f"值符本宮必須為1..9：{chief_origin_palace}")
    if chief_target_palace not in range(1, 10):
        raise ValueError(f"值符落宮必須為1..9：{chief_target_palace}")

    placed: dict[int, str] = {}
    for offset in range(9):
        star_home = _advance_numeric_palace(chief_origin_palace, offset)
        destination = _advance_numeric_palace(chief_target_palace, offset)
        placed[destination] = _QIMEN_STAR_BY_NUMERIC_HOME[star_home]
    return placed


def riqimen_door_plate(day_ganzhi: str) -> dict[int, str]:
    """Place eight doors from the Yuanling 休門 anchor, always forward.

    The primary text gives the exact 60-day 休門 anchor and says 「門皆順」.
    We therefore keep the standard eight-palace Qimen forward ring and never
    send a door through 中五.
    """

    start = rest_door_start_palace(day_ganzhi)
    start_index = PALACE_RING.index(start)
    return {
        PALACE_RING[(start_index + offset) % len(PALACE_RING)]: door
        for offset, door in enumerate(_FORWARD_DOOR_ORDER)
    }


def _heaven_stem_plate(
    earth_plate: dict[int, str],
    day_ganzhi: str,
    day_instrument: str,
    dun: str,
) -> tuple[dict[int, str], int, int, int]:
    """Move the day xun-head instrument onto the visible day stem.

    This is the machine reconstruction of 「本甲旬頭加本日干上論數，視三奇方」.
    For a 甲 day the hidden 甲 is represented by its six-instrument surrogate.
    The stem layer follows the Yin/Yang direction; this is deliberately separate
    from the always-forward star/door flight.
    """

    direction = _dun_direction(dun)
    chief_origin_palace = _raw_stem_palace(earth_plate, day_instrument)
    day_stem = day_ganzhi[0]
    visible_day_stem = day_instrument if day_stem == "甲" else day_stem
    day_stem_palace = _raw_stem_palace(earth_plate, visible_day_stem)
    steps = _steps_between(chief_origin_palace, day_stem_palace, direction)

    heaven = {
        _advance_numeric_palace(palace, steps, direction): stem
        for palace, stem in earth_plate.items()
    }
    return heaven, chief_origin_palace, day_stem_palace, steps


def build_riqimen_base(
    event_at: datetime,
    timezone_name: str,
) -> dict[str, object]:
    """Build the source-crosschecked Yuanling Ri-Qimen reconstruction.

    The object remains independent from Yanshu Qiyao. It does not reuse the
    production Shijia rotating-star placement. Yuanling's own earth-plate,
    day-xun, through-palace star flight and 60-day door anchor are retained as
    a separate research method.
    """

    calendar = build_calendar_context(event_at, timezone_name)
    dun = determine_dun(calendar.solar_term)
    yuan, fu_head_day = determine_yuan(calendar.day_ganzhi)
    ju = determine_ju(calendar.solar_term, yuan)
    earth_plate = deploy_earth_plate(ju, dun)

    day_xun, day_instrument, _, day_offset = xun_for(calendar.day_ganzhi)
    (
        heaven_stem_plate,
        chief_origin_palace,
        day_stem_palace,
        stem_shift_steps,
    ) = _heaven_stem_plate(
        earth_plate,
        calendar.day_ganzhi,
        day_instrument,
        dun,
    )

    chief_star = _QIMEN_STAR_BY_NUMERIC_HOME[chief_origin_palace]
    star_plate = chuangong_star_plate(chief_origin_palace, day_stem_palace)
    door_plate = riqimen_door_plate(calendar.day_ganzhi)
    three_wonder_palaces = {
        stem: next(
            palace for palace, value in heaven_stem_plate.items() if value == stem
        )
        for stem in ("乙", "丙", "丁")
    }

    return {
        "kind": "YUANLING_RI_QIMEN_BASE_V2",
        "status": "SOURCE_CROSSCHECKED_RECONSTRUCTION_READY",
        "calendar": {
            "local_datetime": calendar.local_datetime.isoformat(),
            "timezone": timezone_name,
            "solar_term": calendar.solar_term,
            "day_ganzhi": calendar.day_ganzhi,
            "hour_ganzhi": calendar.hour_ganzhi,
            "dun": dun,
            "yuan": yuan,
            "ju": ju,
            "ju_label": f"{dun}{ju}局",
        },
        "source_reconstructed": {
            "earth_plate": earth_plate,
            "heaven_stem_plate": heaven_stem_plate,
            "three_wonder_palaces": three_wonder_palaces,
            "rest_door_start_palace": rest_door_start_palace(calendar.day_ganzhi),
            "door_plate": door_plate,
            "day_xun": day_xun,
            "day_xun_head_instrument": day_instrument,
            "day_xun_offset": day_offset,
            "fu_head_day": fu_head_day,
            "chief_origin_palace": chief_origin_palace,
            "chief_origin_palace_name": PALACES[chief_origin_palace]["name"],
            "chief_star": chief_star,
            "chief_star_target_palace": day_stem_palace,
            "chief_star_target_palace_name": PALACES[day_stem_palace]["name"],
            "chuangong_star_plate": star_plate,
            "stem_shift_steps": stem_shift_steps,
        },
        "algorithm_resolution": {
            "day_xun_head_to_day_stem": {
                "status": "PRIMARY_TEXT_RECONSTRUCTED",
                "rule": "本甲旬頭加本日干；甲日以旬頭所遁六儀代表隱甲。",
                "direction": "陽遁順、陰遁逆",
            },
            "chuangong": {
                "status": "RESOLVED_BY_PRIMARY_TEXT_PLUS_DAY_QIMEN_CROSSCHECK",
                "rule": "值符之上星加本日干後，九星按宮數順飛，穿中五，9後回1。",
                "traversal": [1, 2, 3, 4, 5, 6, 7, 8, 9],
                "uses_production_rotating_ring": False,
            },
            "star_identity": {
                "status": "RESOLVED_AS_QIMEN_NINE_STAR_LAYER",
                "registry": _QIMEN_STAR_BY_NUMERIC_HOME,
                "rule": "日奇門此處的值符之上星承接卷一奇門九星（天蓬至天英），不得與演數一白至九紫合併。",
            },
            "door_flight": {
                "status": "PRIMARY_ANCHOR_PLUS_FORWARD_RULE",
                "rule": "六十日表定休門起宮；八門依標準八宮環順布，不入中五。",
                "always_forward": True,
            },
        },
        "unresolved": [
            {
                "id": "RIQIMEN_PRIMARY_TEXT_END_TO_END_GOLDEN_CASE",
                "status": "NON_BLOCKING_CROSSCHECK_GAP",
                "rule": (
                    "《元靈經》此節未附一個從節氣、局數一路排到完整星門盤的 worked example；"
                    "穿宮 mechanics 已由同系日奇門文本交叉鎖定，但仍保留 authority label。"
                ),
            }
        ],
        "source_ids": [
            "yuanling.vol1.riqimen",
            "yuanling.vol1.shijia_nine_stars",
            "yuanling.vol1.solar_term_ju",
            "qimen-tongzong-ctext-day-qimen",
        ],
        "authority": "YUANLING_PRIMARY_TEXT_PLUS_CROSSCHECKED_DAY_QIMEN_RECONSTRUCTION",
        "boundary": (
            "這是日奇門 source-crosschecked reconstruction，不是 production 時家轉盤盤的替身；"
            "亦不把天蓬/天芮等日奇門九星靜默等同演數一白/二黑等數術九星。"
        ),
    }
