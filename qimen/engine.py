from __future__ import annotations

from datetime import datetime

from .calendar import SEXAGENARY, build_calendar_context, sexagenary_index, xun_for
from .constants import (
    BRANCH_PALACE,
    DEITIES,
    DOOR_BY_HOME,
    DOOR_ELEMENT,
    DOOR_HOME,
    ELEMENT_CONTROLS,
    FIVE_NOT_MEET,
    HORSE_BRANCH,
    NAMED_STEM_PAIRS,
    OPPOSITE_PALACE,
    PALACE_RING,
    PALACES,
    SIX_INSTRUMENT_PUNISHMENT,
    SOLAR_TERM_JU,
    STAR_BY_HOME,
    STEMS,
    THREE_WONDER_PALACES,
    THREE_WONDER_TOMBS,
    VISIBLE_STEMS,
    YANG_TERMS,
    YUAN_BY_HEAD_BRANCH,
)
from .models import CalendarContext, MethodConfig, PalaceState, PatternHit, QimenBoard
from .patterns import details


def _effective_palace(number: int) -> int:
    return 2 if number == 5 else number


def _advance_numeric_palace(start: int, steps: int, dun: str) -> int:
    direction = 1 if dun == "陽遁" else -1
    return ((start - 1 + direction * steps) % 9) + 1


def _ring_shift(origin: int, target: int) -> int:
    return (PALACE_RING.index(target) - PALACE_RING.index(origin)) % 8


def _rotate_home_map(items: dict[int, str], shift: int) -> dict[int, str]:
    placed: dict[int, str] = {}
    for home, item in items.items():
        destination = PALACE_RING[(PALACE_RING.index(home) + shift) % 8]
        placed[destination] = item
    return placed


def determine_fu_head(day_ganzhi: str) -> str:
    """Return the 甲/己 five-day symbol head used by Chaibu."""

    index = sexagenary_index(day_ganzhi)
    stem_index = STEMS.index(day_ganzhi[0])
    return SEXAGENARY[(index - stem_index % 5) % 60]


def determine_yuan(day_ganzhi: str) -> tuple[str, str]:
    fu_head = determine_fu_head(day_ganzhi)
    return YUAN_BY_HEAD_BRANCH[fu_head[1]], fu_head


def determine_dun(term: str) -> str:
    if term in YANG_TERMS:
        return "陽遁"
    if term in SOLAR_TERM_JU:
        return "陰遁"
    raise ValueError(f"節氣不在定局表：{term}")


def determine_ju(term: str, yuan: str) -> int:
    yuan_index = {"上元": 0, "中元": 1, "下元": 2}[yuan]
    try:
        return SOLAR_TERM_JU[term][yuan_index]
    except KeyError as exc:
        raise ValueError(f"無法定局：{term} {yuan}") from exc


def deploy_earth_plate(ju: int, dun: str) -> dict[int, str]:
    direction = 1 if dun == "陽遁" else -1
    earth: dict[int, str] = {}
    for offset, stem in enumerate(VISIBLE_STEMS):
        palace = ((ju - 1 + direction * offset) % 9) + 1
        earth[palace] = stem
    return earth


def _raw_stem_palace(earth: dict[int, str], stem: str) -> int:
    for palace, value in earth.items():
        if value == stem:
            return palace
    raise ValueError(f"地盤找不到天干：{stem}")


def _stem_palace_with_center_policy(earth: dict[int, str], stem: str) -> int:
    return _effective_palace(_raw_stem_palace(earth, stem))


def _new_palaces(earth: dict[int, str]) -> dict[int, PalaceState]:
    states: dict[int, PalaceState] = {}
    for number, meta in PALACES.items():
        states[number] = PalaceState(
            number=number,
            name=meta["name"],
            trigram=meta["trigram"],
            direction=meta["direction"],
            element=meta["element"],
            earth_stem=earth[number],
        )
    states[2].earth_hidden_stems.append(earth[5])
    states[2].notes.append(f"中五寄干：{earth[5]}")
    states[5].notes.append("中五依本系統規則寄坤二")
    return states


def _place_stars_and_heaven_stems(
    states: dict[int, PalaceState],
    earth: dict[int, str],
    chief_origin_raw: int,
    chief_target: int,
) -> tuple[str, int]:
    chief_star = PALACES[chief_origin_raw]["star"]
    carrier_home = _effective_palace(chief_origin_raw)
    shift = _ring_shift(carrier_home, chief_target)
    placed_stars = _rotate_home_map(STAR_BY_HOME, shift)

    for destination, star in placed_stars.items():
        home = next(key for key, value in STAR_BY_HOME.items() if value == star)
        states[destination].stars.append(star)
        states[destination].heaven_stems.append(earth[home])
        if home == 2:
            states[destination].stars.append("天禽")
            states[destination].heaven_stems.append(earth[5])

    if chief_origin_raw == 5:
        target_state = states[chief_target]
        target_state.stars = ["天禽", "天芮"]
        target_state.heaven_stems = [earth[5], earth[2]]
    return chief_star, shift


def _place_doors(
    states: dict[int, PalaceState],
    chief_origin_raw: int,
    chief_target: int,
) -> str:
    chief_door = PALACES[chief_origin_raw]["door"] or "死門"
    shift = _ring_shift(DOOR_HOME[chief_door], chief_target)
    for destination, door in _rotate_home_map(DOOR_BY_HOME, shift).items():
        states[destination].door = door
    return chief_door


def _place_deities(states: dict[int, PalaceState], start: int, dun: str) -> None:
    direction = 1 if dun == "陽遁" else -1
    start_index = PALACE_RING.index(start)
    for offset, deity in enumerate(DEITIES):
        palace = PALACE_RING[(start_index + direction * offset) % 8]
        states[palace].deity = deity


def _pattern_hit(name: str, category: str, palace: int | None, condition: str) -> PatternHit:
    reading, caution, source_id = details(name)
    return PatternHit(name, category, palace, condition, reading, caution, source_id)


def _detect_patterns(
    states: dict[int, PalaceState],
    calendar: CalendarContext,
) -> list[PatternHit]:
    hits: list[PatternHit] = []

    for number, state in states.items():
        earth_stems = [state.earth_stem, *state.earth_hidden_stems]
        for heaven in state.heaven_stems:
            for earth in earth_stems:
                pair = NAMED_STEM_PAIRS.get((heaven, earth))
                if pair:
                    name, category = pair
                    hits.append(_pattern_hit(name, category, number, f"{state.name}：天盤{heaven}加地盤{earth}"))

        for heaven in state.heaven_stems:
            if THREE_WONDER_PALACES.get(heaven) == number:
                hits.append(_pattern_hit("三奇升殿", "吉格", number, f"{heaven}奇臨{state.name}"))
            if THREE_WONDER_TOMBS.get(heaven) == number:
                hits.append(_pattern_hit("三奇入墓", "狀態格", number, f"{heaven}奇入{state.name}墓位"))
            if SIX_INSTRUMENT_PUNISHMENT.get(heaven) == number:
                hits.append(_pattern_hit("六儀擊刑", "狀態格", number, f"{heaven}儀臨擊刑宮{number}"))

        if state.door:
            door_element = DOOR_ELEMENT[state.door]
            if ELEMENT_CONTROLS[door_element] == state.element:
                hits.append(_pattern_hit("門迫", "宮門關係", number, f"{state.door}{door_element}克{state.name}{state.element}"))
            if ELEMENT_CONTROLS[state.element] == door_element:
                hits.append(_pattern_hit("宮迫", "宮門關係", number, f"{state.name}{state.element}克{state.door}{door_element}"))

    star_positions = {
        star: number
        for number, state in states.items()
        for star in state.stars
        if star != "天禽"
    }
    door_positions = {state.door: number for number, state in states.items() if state.door}
    if all(star_positions.get(star) == home for home, star in STAR_BY_HOME.items()):
        hits.append(_pattern_hit("星伏吟", "盤勢", None, "八星全回本宮"))
    if all(door_positions.get(door) == home for home, door in DOOR_BY_HOME.items()):
        hits.append(_pattern_hit("門伏吟", "盤勢", None, "八門全回本宮"))
    if all(star_positions.get(star) == OPPOSITE_PALACE[home] for home, star in STAR_BY_HOME.items()):
        hits.append(_pattern_hit("星反吟", "盤勢", None, "八星全臨對宮"))
    if all(door_positions.get(door) == OPPOSITE_PALACE[home] for home, door in DOOR_BY_HOME.items()):
        hits.append(_pattern_hit("門反吟", "盤勢", None, "八門全臨對宮"))

    if FIVE_NOT_MEET[calendar.day_ganzhi[0]] == calendar.hour_ganzhi[0]:
        hits.append(_pattern_hit(
            "五不遇時", "時格", None,
            f"日干{calendar.day_ganzhi[0]}受時干{calendar.hour_ganzhi[0]}同陰陽相剋",
        ))

    unique: dict[tuple[str, int | None, str], PatternHit] = {}
    for hit in hits:
        unique[(hit.name, hit.palace, hit.condition)] = hit
    return list(unique.values())


def cast_qimen(
    local_datetime: datetime,
    timezone_name: str,
    *,
    method: MethodConfig | None = None,
    calendar: CalendarContext | None = None,
) -> QimenBoard:
    """Cast one deterministic Shijia rotating-plate chart.

    ``calendar`` can be injected for deterministic tests and archived rebuilds. In
    normal operation it is produced from the exact event instant and IANA timezone.
    """

    selected_method = method or MethodConfig()
    if selected_method.plate_method != "轉盤" or selected_method.ju_method != "拆補法":
        raise NotImplementedError("v1.0 僅實作並驗證轉盤／拆補法；其他流派只進知識庫，不混算")

    context = calendar or build_calendar_context(local_datetime, timezone_name)
    dun = determine_dun(context.solar_term)
    yuan, fu_head_day = determine_yuan(context.day_ganzhi)
    ju = determine_ju(context.solar_term, yuan)
    earth = deploy_earth_plate(ju, dun)
    states = _new_palaces(earth)

    hour_xun, instrument, void_branches, hour_offset = xun_for(context.hour_ganzhi)
    chief_origin_raw = _raw_stem_palace(earth, instrument)
    visible_hour_stem = instrument if context.hour_ganzhi[0] == "甲" else context.hour_ganzhi[0]
    chief_star_target = _stem_palace_with_center_policy(earth, visible_hour_stem)

    chief_star, _ = _place_stars_and_heaven_stems(
        states, earth, chief_origin_raw, chief_star_target
    )
    chief_door_target_raw = _advance_numeric_palace(chief_origin_raw, hour_offset, dun)
    chief_door_target = _effective_palace(chief_door_target_raw)
    chief_door = _place_doors(states, chief_origin_raw, chief_door_target)
    _place_deities(states, chief_star_target, dun)

    void_palaces = {BRANCH_PALACE[branch] for branch in void_branches}
    for palace in void_palaces:
        states[palace].is_void = True
        states[palace].notes.append(f"旬空：{'、'.join(void_branches)}")

    hour_branch = context.hour_ganzhi[1]
    horse_branch = HORSE_BRANCH[hour_branch]
    horse_palace = BRANCH_PALACE[horse_branch]
    states[horse_palace].is_horse = True
    states[horse_palace].notes.append(f"時馬：{horse_branch}")

    patterns = _detect_patterns(states, context)
    warnings = [
        "此盤採事件所在地民用時；若改用真太陽時，必須另存經度與換算結果。",
        "轉盤、飛盤、拆補、置閏及中五寄宮不可混算；本盤方法版本已鎖定。",
        "格局只修飾條件，不單獨輸出勝率、固定比分、醫療或投注結論。",
    ]

    return QimenBoard(
        method=selected_method,
        calendar=context,
        dun=dun,
        yuan=yuan,
        ju=ju,
        ju_label=f"{dun}{ju}局",
        fu_head_day=fu_head_day,
        hour_xun=hour_xun,
        xun_head_instrument=instrument,
        chief_star=chief_star,
        chief_door=chief_door,
        chief_star_palace=chief_star_target,
        chief_door_palace=chief_door_target,
        void_branches=void_branches,
        horse_branch=horse_branch,
        horse_palace=horse_palace,
        palaces=states,
        patterns=patterns,
        warnings=warnings,
        generated_at=datetime.now(tz=context.local_datetime.tzinfo),
    )
