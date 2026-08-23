from __future__ import annotations

from qimen.calendar import BRANCHES, sexagenary_index

from .stars import numeric_star_by_alias


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


def collateral_daily_nine_star_chart(day_ganzhi: str, dun: str) -> dict[int, str]:
    """Reconstruct a day-nine-star chart from collateral 金函玉鏡 rules.

    This is NOT promoted to a Yuanling-primary rule.  It is stored as a
    collateral candidate because the source gives exact 甲子 anchors and the
    same 太乙/攝提/... sequence found around the Yuanling material.
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


def build_collateral_qiyao_reconstruction(
    day_ganzhi: str,
    hour_ganzhi: str,
    dun: str,
) -> dict[str, object]:
    """Expose reconstructable candidates without filling Yuanling seven-factor facts."""

    number_palace = collateral_number_palace(day_ganzhi, hour_ganzhi[1], dun)
    chart = collateral_daily_nine_star_chart(day_ganzhi, dun)
    star_at_number_palace = chart[number_palace]
    center_star = chart[5]
    star_record = numeric_star_by_alias(star_at_number_palace)
    center_record = numeric_star_by_alias(center_star)

    return {
        "kind": "YUANLING_COLLATERAL_QIYAO_RECONSTRUCTION_V1",
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
            "possible_role": "飛星候選",
            "not_proven_role": "數主",
            "adopt_as_primary_factor": False,
        },
        "center_daily_star_candidate": {
            "star_name": center_star,
            "numeric_star": center_record.color_name,
            "possible_role": "直日星候選",
            "adopt_as_primary_factor": False,
        },
        "non_equivalence_rules": [
            "數宮候選不是數值候選",
            "數宮宮數不得直接轉足球總進球",
            "數宮上的日遁九星不得自動等同數主",
            "中宮日遁星不得自動等同直日星",
            "旁證重建不得升格為元靈經原文明文",
        ],
        "source_ids": [
            "qimen-baojian-dongting-collateral",
            "jinhanyujing-ctext-day-nine-stars",
        ],
    }
