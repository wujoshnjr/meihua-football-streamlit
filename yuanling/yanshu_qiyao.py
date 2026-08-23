from __future__ import annotations

from datetime import datetime
from typing import Any

from qimen.calendar import build_calendar_context
from qimen.constants import ELEMENT_CONTROLS, ELEMENT_GENERATES, PALACES
from qimen.engine import determine_dun

from .collateral import build_collateral_qiyao_reconstruction
from .riqimen import build_riqimen_base
from .stars import numeric_star, star_registry_audit


ALLOWED_MODES = {"QIYAO_RAW", "RIQIMEN_QIYAO_EXPERIMENT"}


def _factor(
    name: str,
    value: Any = None,
    *,
    status: str | None = None,
    note: str = "",
) -> dict[str, Any]:
    resolved = value is not None
    return {
        "name": name,
        "status": status or ("RESOLVED_INPUT" if resolved else "UNRESOLVED_BY_SOURCE_AUDIT"),
        "value": value,
        "note": note,
    }


def _chief_landing_relation(star_number: int, palace: int) -> dict[str, Any]:
    star = numeric_star(star_number)
    try:
        palace_element = str(PALACES[palace]["element"])
    except KeyError as exc:
        raise ValueError(f"數主落宮必須為1..9宮：{palace}") from exc

    if palace_element == star.normalized_element:
        state = "和"
        explanation = "落宮五行與數主 normalized element 同類。"
    elif ELEMENT_GENERATES[palace_element] == star.normalized_element:
        state = "生"
        explanation = "落宮五行生數主；此方向與卷一『黑星遁離為生』例一致。"
    elif ELEMENT_CONTROLS[palace_element] == star.normalized_element:
        state = "難"
        explanation = "落宮五行克數主；此方向與卷一『黑星遁震巽為難』例一致。"
    else:
        state = "未分類"
        explanation = "原節歌訣未在已校勘例句中明示此生克方向的名稱，保留不分類。"

    return {
        "star_number": star.number,
        "star_name": star.color_name,
        "star_element": star.normalized_element,
        "star_element_authority": star.element_authority,
        "landing_palace": palace,
        "landing_palace_name": PALACES[palace]["name"],
        "landing_palace_element": palace_element,
        "source_song_state": state,
        "explanation": explanation,
        "authority": "SOURCE_EXAMPLE_DIRECTION_PLUS_PROJECT_NORMALIZED_ELEMENTS",
    }


def build_qiyao_review(
    event_at: datetime,
    timezone_name: str,
    *,
    mode: str = "QIYAO_RAW",
    number_palace: int | None = None,
    number_chief_star_number: int | None = None,
    number_chief_landing_palace: int | None = None,
    flying_star: Any = None,
    entry_door: Any = None,
    daily_star_number: int | None = None,
) -> dict[str, Any]:
    """Build seven-factor review while keeping unresolved classical rules visible.

    Raw research inputs can be supplied for fields whose Yuanling algorithm is not
    yet fully reconstructed.  A separate collateral block gives candidate
    mechanics from related Qimen texts but does not silently populate the primary
    seven factors or convert palace numbers into football scores.
    """

    if mode not in ALLOWED_MODES:
        raise ValueError(f"未知演數模式：{mode}")
    if number_chief_star_number is None and number_chief_landing_palace is not None:
        raise ValueError("提供數主落宮時必須同時提供數主星號")
    if number_chief_star_number is not None:
        numeric_star(number_chief_star_number)
    if daily_star_number is not None:
        numeric_star(daily_star_number)

    calendar = build_calendar_context(event_at, timezone_name)
    dun = determine_dun(calendar.solar_term)
    collateral = build_collateral_qiyao_reconstruction(
        calendar.day_ganzhi,
        calendar.hour_ganzhi,
        dun,
    )
    factors = [
        _factor(
            "數宮",
            number_palace,
            note=(
                "《元靈經》本節完整取法仍待 reconstruction；旁證文本已有候選算法，"
                "但不自動升格為 primary factor，更不得把宮數直接當球數。"
            ),
        ),
        _factor(
            "數主",
            (
                {
                    "star": numeric_star(number_chief_star_number).__dict__,
                    "landing_palace": number_chief_landing_palace,
                }
                if number_chief_star_number is not None
                else None
            ),
            note="原典明示『遁至本時之星即為數主』，但完整飛遁算法尚未鎖定。",
        ),
        _factor(
            "飛星",
            flying_star,
            note="旁證可重建數宮上的日遁九星候選，但尚不直接寫回《元靈經》飛星欄。",
        ),
        _factor(
            "入門",
            entry_door,
            note="《奇門寶鑑》旁證作『八門』；不得直接借用時家盤值使門作替代。",
        ),
        _factor(
            "直日星",
            numeric_star(daily_star_number).__dict__ if daily_star_number is not None else None,
            note=(
                "卷三有中宮值日九星歌訣；旁證日遁九星可得中宮星候選，"
                "但尚未證成兩者必然等同。"
            ),
        ),
        _factor(
            "日干",
            calendar.day_ganzhi[0],
            status="CALENDAR_FACT",
            note="由事件所在地 civil time 的日柱取得。",
        ),
        _factor(
            "時支",
            calendar.hour_ganzhi[1],
            status="CALENDAR_FACT",
            note="由事件所在地 civil time 的時柱取得。",
        ),
    ]

    chief_state = None
    if number_chief_star_number is not None and number_chief_landing_palace is not None:
        chief_state = _chief_landing_relation(
            number_chief_star_number,
            number_chief_landing_palace,
        )

    riqimen = None
    if mode == "RIQIMEN_QIYAO_EXPERIMENT":
        riqimen = build_riqimen_base(event_at, timezone_name)

    unresolved = [
        factor["name"]
        for factor in factors
        if factor["status"] == "UNRESOLVED_BY_SOURCE_AUDIT"
    ]
    return {
        "kind": "YUANLING_YANSHU_QIYAO_REVIEW_V1",
        "mode": mode,
        "status": "PARTIAL_SOURCE_GROUNDED",
        "event": {
            "local_datetime": calendar.local_datetime.isoformat(),
            "timezone": timezone_name,
            "solar_term": calendar.solar_term,
            "day_ganzhi": calendar.day_ganzhi,
            "hour_ganzhi": calendar.hour_ganzhi,
            "dun": dun,
        },
        "seven_factors": factors,
        "number_chief_landing_state": chief_state,
        "numeric_star_registry": star_registry_audit(),
        "collateral_reconstruction": collateral,
        "riqimen_experiment_input": riqimen,
        "raw_numeric_candidates": {
            "status": "DISABLED_UNTIL_ALGORITHM_SOURCE_LOCK",
            "values": [],
            "rule": "No palace-number-to-goals mapping and no post-match fitting.",
        },
        "uncertainty": [
            {
                "id": f"UNRESOLVED_{name}",
                "severity": "BLOCKS_AUTOMATIC_CALCULATION",
            }
            for name in unresolved
        ],
        "authority": "YUANLING_SOURCE_REVIEW_WITH_EXPLICIT_PROJECT_NORMALIZATION",
        "boundary": (
            "演數七要與日奇門保持獨立；旁證 reconstruction 也與 primary factors 分層。"
            "RIQIMEN_QIYAO_EXPERIMENT 只是一條可測試橋接，不宣稱《元靈經》明文要求"
            "七要必須以日奇門盤為底。"
        ),
    }
