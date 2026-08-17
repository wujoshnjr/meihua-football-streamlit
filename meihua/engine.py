from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

MEIHUA_ENGINE_VERSION = "jarvis-meihua-year-month-day-hour-v0.1.0"

TRIGRAM_BY_NUMBER = {
    1: "乾",
    2: "兌",
    3: "離",
    4: "震",
    5: "巽",
    6: "坎",
    7: "艮",
    8: "坤",
}
TRIGRAM_NUMBER = {name: number for number, name in TRIGRAM_BY_NUMBER.items()}
TRIGRAM_LINES = {
    "乾": (1, 1, 1),
    "兌": (1, 1, 0),
    "離": (1, 0, 1),
    "震": (1, 0, 0),
    "巽": (0, 1, 1),
    "坎": (0, 1, 0),
    "艮": (0, 0, 1),
    "坤": (0, 0, 0),
}
TRIGRAM_FROM_LINES = {lines: name for name, lines in TRIGRAM_LINES.items()}
TRIGRAM_ELEMENT = {
    "乾": "金",
    "兌": "金",
    "離": "火",
    "震": "木",
    "巽": "木",
    "坎": "水",
    "艮": "土",
    "坤": "土",
}
BRANCH_NUMBER = {
    "子": 1,
    "丑": 2,
    "寅": 3,
    "卯": 4,
    "辰": 5,
    "巳": 6,
    "午": 7,
    "未": 8,
    "申": 9,
    "酉": 10,
    "戌": 11,
    "亥": 12,
}
GENERATES = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
CONTROLS = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}


@dataclass(frozen=True)
class MeihuaSnapshot:
    schema_version: str
    event_local_at: datetime
    timezone_name: str
    lunar_year_branch: str
    lunar_month: int
    lunar_day: int
    hour_branch: str
    upper_trigram: str
    lower_trigram: str
    moving_line: int
    body_trigram: str
    use_trigram: str
    mutual_upper_trigram: str
    mutual_lower_trigram: str
    changed_upper_trigram: str
    changed_lower_trigram: str
    changed_use_trigram: str
    body_use_relation: str
    mutual_upper_relation_to_body: str
    mutual_lower_relation_to_body: str
    changed_use_relation_to_body: str
    body_season_state: str

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["event_local_at"] = self.event_local_at.isoformat()
        return payload


def _remainder_index(total: int, modulus: int) -> int:
    remainder = total % modulus
    return modulus if remainder == 0 else remainder


def _relation(other_trigram: str, body_trigram: str) -> str:
    other = TRIGRAM_ELEMENT[other_trigram]
    body = TRIGRAM_ELEMENT[body_trigram]
    if other == body:
        return "比和"
    if GENERATES[other] == body:
        return "生體"
    if GENERATES[body] == other:
        return "體生用"
    if CONTROLS[other] == body:
        return "克體"
    if CONTROLS[body] == other:
        return "體克用"
    raise AssertionError("五行關係不完整")


def _season_state(trigram: str, lunar_month: int) -> str:
    month = abs(lunar_month)
    if month not in range(1, 13):
        raise ValueError("農曆月份必須在 1..12")
    element = TRIGRAM_ELEMENT[trigram]
    if month in (3, 6, 9, 12):
        if element == "土":
            return "旺"
        if element == "水":
            return "衰"
        return "平"
    season = (
        "春" if month in (1, 2) else
        "夏" if month in (4, 5) else
        "秋" if month in (7, 8) else
        "冬"
    )
    thriving = {"春": "木", "夏": "火", "秋": "金", "冬": "水"}[season]
    declining = {"春": "土", "夏": "金", "秋": "木", "冬": "火"}[season]
    if element == thriving:
        return "旺"
    if element == declining:
        return "衰"
    return "平"


def build_meihua_snapshot_from_numbers(
    *,
    event_local_at: datetime,
    timezone_name: str,
    year_branch: str,
    lunar_month: int,
    lunar_day: int,
    hour_branch: str,
) -> MeihuaSnapshot:
    """Build the fixed year-month-day-hour Meihua snapshot.

    The arithmetic follows the traditional year/month/day/hour example: year +
    lunar month + lunar day chooses the upper trigram; adding the branch-hour
    number chooses the lower trigram and moving line. The research convention is
    event-location civil time and the same deterministic method for every match.
    """

    if event_local_at.tzinfo is None:
        raise ValueError("event_local_at 必須含時區")
    if year_branch not in BRANCH_NUMBER:
        raise ValueError(f"無效年支：{year_branch}")
    if hour_branch not in BRANCH_NUMBER:
        raise ValueError(f"無效時支：{hour_branch}")
    month = abs(lunar_month)
    if month not in range(1, 13):
        raise ValueError("農曆月份必須在 1..12")
    if lunar_day not in range(1, 31):
        raise ValueError("農曆日必須在 1..30")

    upper_total = BRANCH_NUMBER[year_branch] + month + lunar_day
    full_total = upper_total + BRANCH_NUMBER[hour_branch]
    upper = TRIGRAM_BY_NUMBER[_remainder_index(upper_total, 8)]
    lower = TRIGRAM_BY_NUMBER[_remainder_index(full_total, 8)]
    moving_line = _remainder_index(full_total, 6)

    original_lines = TRIGRAM_LINES[lower] + TRIGRAM_LINES[upper]
    mutual_lower = TRIGRAM_FROM_LINES[original_lines[1:4]]
    mutual_upper = TRIGRAM_FROM_LINES[original_lines[2:5]]
    changed_lines = list(original_lines)
    changed_lines[moving_line - 1] = 1 - changed_lines[moving_line - 1]
    changed_lower = TRIGRAM_FROM_LINES[tuple(changed_lines[:3])]
    changed_upper = TRIGRAM_FROM_LINES[tuple(changed_lines[3:])]

    if moving_line <= 3:
        body = upper
        use = lower
        changed_use = changed_lower
    else:
        body = lower
        use = upper
        changed_use = changed_upper

    return MeihuaSnapshot(
        schema_version=MEIHUA_ENGINE_VERSION,
        event_local_at=event_local_at,
        timezone_name=timezone_name,
        lunar_year_branch=year_branch,
        lunar_month=month,
        lunar_day=lunar_day,
        hour_branch=hour_branch,
        upper_trigram=upper,
        lower_trigram=lower,
        moving_line=moving_line,
        body_trigram=body,
        use_trigram=use,
        mutual_upper_trigram=mutual_upper,
        mutual_lower_trigram=mutual_lower,
        changed_upper_trigram=changed_upper,
        changed_lower_trigram=changed_lower,
        changed_use_trigram=changed_use,
        body_use_relation=_relation(use, body),
        mutual_upper_relation_to_body=_relation(mutual_upper, body),
        mutual_lower_relation_to_body=_relation(mutual_lower, body),
        changed_use_relation_to_body=_relation(changed_use, body),
        body_season_state=_season_state(body, month),
    )


def build_meihua_snapshot(event_at: datetime, timezone_name: str) -> MeihuaSnapshot:
    """Build a Meihua snapshot from an official event instant and IANA zone.

    ``lunar_python`` is used only to obtain the lunar month/day and year/hour
    branches from the event-location civil clock. This is a JARVIS research
    convention chosen for reproducibility; it is not presented as the only
    traditional Meihua timing convention.
    """

    try:
        zone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"找不到 IANA 時區：{timezone_name}") from exc
    local = event_at.astimezone(zone) if event_at.tzinfo is not None else event_at.replace(tzinfo=zone)
    try:
        from lunar_python import Solar
    except ImportError as exc:
        raise RuntimeError("缺少 lunar_python==1.4.8") from exc
    lunar = Solar.fromYmdHms(
        local.year,
        local.month,
        local.day,
        local.hour,
        local.minute,
        local.second,
    ).getLunar()
    return build_meihua_snapshot_from_numbers(
        event_local_at=local,
        timezone_name=timezone_name,
        year_branch=lunar.getYearZhi(),
        lunar_month=lunar.getMonth(),
        lunar_day=lunar.getDay(),
        hour_branch=lunar.getTimeZhi(),
    )
