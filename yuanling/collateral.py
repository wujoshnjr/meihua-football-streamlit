from __future__ import annotations

from qimen.calendar import BRANCHES, sexagenary_index

from .stars import numeric_star, numeric_star_by_alias


DAILY_STAR_ORDER: tuple[str, ...] = (
    "太乙",
    "攝提",
    "軒轅",
    "招搖",
    "天符",
    "青龍",
    "咸池",
    "太陰",
    "天乙",
)


def _advance_palace(start: int, steps: int, direction: int) -> int:
    return ((start - 1 + direction * steps) % 9) + 1


def _direction(dun: str) -> int:
    if dun == "陽遁":
        return 1
    if dun == "陰遁":
        return -1
    raise ValueError(f"遁法必須為陽遁或陰遁：{dun}")


def _star_landing_palace(chart: dict[int, str], star_name: str) -> int:
    for palace, value in chart.items():
        if value == star_name:
            return palace
    raise ValueError(f"日遁九星盤找不到：{star_name}")


def collateral_daily_nine_star_chart(day_ganzhi: str, dun: str) -> dict[int, str]:
    """Reconstruct the day-nine-star chart from 金函玉鏡 collateral rules.

    冬至後甲子太乙起艮八而順飛；夏至後甲子太乙起坤二而逆飛。
    This is exact collateral mechanics, but it is not silently promoted to a
    Yuanling-primary rule.
    """

    direction = _direction(dun)
    day_index = sexagenary_index(day_ganzhi)
    taiyi_jiazi_palace = 8 if dun == "陽遁" else 2
    taiyi_palace = _advance_palace(taiyi_jiazi_palace, day_index, direction)
    return {
        _advance_palace(taiyi_palace, star_offset, direction): star_name
        for star_offset, star_name in enumerate(DAILY_STAR_ORDER)
    }


def collateral_day_stem_palace(day_stem: str, dun: str) -> int:
    """Return the Dongting/Qimen-Baojian candidate palace for the day stem."""

    stems = "甲乙丙丁戊己庚辛壬癸"
    try:
        offset = stems.index(day_stem)
    except ValueError as exc:
        raise ValueError(f"無效日干：{day_stem}") from exc
    return _advance_palace(5, offset, _direction(dun))


def collateral_number_palace(day_ganzhi: str, hour_branch: str, dun: str) -> int:
    """Reconstruct the collateral time palace used immediately before 七要.

    子 starts at the day-stem palace. 丑 through 申 advance in the same
    direction. 酉/戌/亥 repeat 子/丑/寅, matching the collateral text.
    """

    try:
        branch_index = BRANCHES.index(hour_branch)
    except ValueError as exc:
        raise ValueError(f"無效時支：{hour_branch}") from exc
    hour_offset = branch_index % 9
    day_palace = collateral_day_stem_palace(day_ganzhi[0], dun)
    return _advance_palace(day_palace, hour_offset, _direction(dun))


def collateral_qiyao_star_roles(
    day_ganzhi: str,
    hour_ganzhi: str,
    dun: str,
) -> dict[str, object]:
    """Resolve 數主 / 飛星 / 直日星 as three different lookup roles.

    The Yuanling sentence itself distinguishes a star whose landing palace is
    inspected from another star that "臨到本宮". Qimen Baojian preserves a
    mechanically coherent parallel passage: when the number palace is 坤二,
    二黑 is the chief and its *landing* is judged separately. The adjacent
    中宮直日九星 section then identifies the center occupant as the value-day
    layer. We expose that relationship without overwriting raw Yuanling slots.
    """

    if len(hour_ganzhi) != 2:
        raise ValueError(f"時干支必須為兩字：{hour_ganzhi}")

    number_palace = collateral_number_palace(day_ganzhi, hour_ganzhi[1], dun)
    chart = collateral_daily_nine_star_chart(day_ganzhi, dun)

    number_chief = numeric_star(number_palace)
    chief_landing = _star_landing_palace(chart, number_chief.qimen_jieqi_alias)

    flying_alias = chart[number_palace]
    flying = numeric_star_by_alias(flying_alias)

    value_day_alias = chart[5]
    value_day = numeric_star_by_alias(value_day_alias)

    return {
        "kind": "YUANLING_QIYAO_STAR_ROLE_RECONSTRUCTION_V1",
        "status": "ROLE_RELATIONSHIP_RESOLVED__IDENTITY_MAPPING_CROSSCHECKED",
        "authority": "YUANLING_ROLE_GRAMMAR_PLUS_QIMEN_BAOJIAN_AND_JINHAN_COLLATERAL",
        "number_palace": number_palace,
        "number_chief": {
            "role": "數主",
            "definition": "數宮所主之本位數術星；重點是追蹤該星現時遁落何宮。",
            "home_palace": number_palace,
            "star_number": number_chief.number,
            "color_name": number_chief.color_name,
            "daily_alias": number_chief.qimen_jieqi_alias,
            "landing_palace": chief_landing,
        },
        "flying_star": {
            "role": "飛星",
            "definition": "當日日遁九星盤中『臨到數宮』的星；查詢方向是宮位→盤上星。",
            "landing_palace": number_palace,
            "star_number": flying.number,
            "color_name": flying.color_name,
            "daily_alias": flying_alias,
        },
        "value_day_star": {
            "role": "直日星",
            "definition": "中宮直日九星層；以當日日遁九星盤的中五占星作 crosschecked reconstruction。",
            "landing_palace": 5,
            "star_number": value_day.number,
            "color_name": value_day.color_name,
            "daily_alias": value_day_alias,
        },
        "relation": {
            "number_chief_lookup": "數宮 -> 本位數術星 -> 該星在當日日遁盤的落宮",
            "flying_star_lookup": "數宮 -> 當日日遁盤臨宮之星",
            "value_day_lookup": "中五 -> 當日日遁盤中宮之星",
            "number_chief_is_not_flying_star_by_definition": True,
            "value_day_is_not_number_chief_by_definition": True,
        },
        "coincidence_flags": {
            "number_chief_equals_flying_star": number_chief.number == flying.number,
            "number_chief_equals_value_day_star": number_chief.number == value_day.number,
            "flying_star_equals_value_day_star": flying.number == value_day.number,
        },
        "textual_variant_warning": {
            "yuanling_transmitted_example": "假如數在乾宮，黑星為主",
            "qimen_baojian_parallel_example": "假如數在坤宮，黑星為主",
            "assessment": (
                "二黑配坤二在數理上自洽；《元靈經》現行傳本文字作乾宮，故本函數把"
                "『數宮本位星』標成 crosschecked reconstruction，而不改寫原典。"
            ),
        },
        "source_ids": [
            "yuanling.vol1.qiyao",
            "yuanling.vol1.number_chief_song",
            "yuanling.vol3.value_day_nine_stars",
            "qimen-baojian-dongting-collateral",
            "jinhanyujing-ctext-day-nine-stars",
        ],
    }


def build_collateral_qiyao_reconstruction(
    day_ganzhi: str,
    hour_ganzhi: str,
    dun: str,
) -> dict[str, object]:
    """Expose reconstructable candidates without silently rewriting Yuanling."""

    number_palace = collateral_number_palace(day_ganzhi, hour_ganzhi[1], dun)
    chart = collateral_daily_nine_star_chart(day_ganzhi, dun)
    star_at_number_palace = chart[number_palace]
    center_star = chart[5]
    star_record = numeric_star_by_alias(star_at_number_palace)
    center_record = numeric_star_by_alias(center_star)
    role_resolution = collateral_qiyao_star_roles(day_ganzhi, hour_ganzhi, dun)

    return {
        "kind": "YUANLING_COLLATERAL_QIYAO_RECONSTRUCTION_V2",
        "authority": "COLLATERAL_QIMEN_TEXT_RECONSTRUCTION",
        "status": "CANDIDATES_ONLY__NOT_PRIMARY_YUANLING_FACTS",
        "inputs": {
            "day_ganzhi": day_ganzhi,
            "hour_ganzhi": hour_ganzhi,
            "dun": dun,
        },
        "number_palace_candidate": {
            "palace": number_palace,
            "source_role": "候選數宮",
            "adopt_as_primary_factor": False,
        },
        "daily_nine_star_chart_candidate": {
            str(palace): star for palace, star in sorted(chart.items())
        },
        "daily_star_at_number_palace_candidate": {
            "star_name": star_at_number_palace,
            "numeric_star": star_record.color_name,
            "role": "飛星",
            "adopt_as_primary_factor": False,
        },
        "center_daily_star_candidate": {
            "star_name": center_star,
            "numeric_star": center_record.color_name,
            "role": "直日星",
            "adopt_as_primary_factor": False,
        },
        "star_role_resolution_candidate": role_resolution,
        "non_equivalence_rules": [
            "數宮候選不是數值候選",
            "數宮宮數不得直接轉足球總進球",
            "數主與飛星是不同查詢角色；盤面偶合相同不代表定義相同",
            "直日星是獨立中宮值日層，不自動等同數主",
            "旁證重建不得改寫《元靈經》乾宮/坤宮傳本文字差異",
        ],
        "source_ids": [
            "qimen-baojian-dongting-collateral",
            "jinhanyujing-ctext-day-nine-stars",
        ],
    }
