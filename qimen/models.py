from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class MethodConfig:
    """Algorithm choices that materially change a Qimen chart."""

    family: str = "時家奇門"
    plate_method: str = "轉盤"
    ju_method: str = "拆補法"
    time_basis: str = "事件所在地民用時"
    zi_hour_boundary: str = "晚子時換日（lunar-python sect=1）"
    center_policy: str = "中五寄坤二，天禽隨天芮"
    deity_policy: str = "八神同名制；陽遁順、陰遁逆"
    host_guest_policy: str = "足球固定：主隊取日干、客隊取時干；甲取值符宮"
    version: str = "shijia-zhuanpan-chaibu-v1.0.0"


@dataclass(frozen=True)
class CalendarContext:
    local_datetime: datetime
    timezone_name: str
    solar_term: str
    solar_term_at: datetime
    next_solar_term: str
    next_solar_term_at: datetime
    year_ganzhi: str
    month_ganzhi: str
    day_ganzhi: str
    hour_ganzhi: str
    day_xun: str
    day_void_branches: tuple[str, str]
    source: str = "lunar_python==1.4.8"
    tzdb_version: str = "unknown"


@dataclass
class PatternHit:
    name: str
    category: str
    palace: int | None
    condition: str
    reading: str
    caution: str
    source_id: str


@dataclass
class PalaceState:
    number: int
    name: str
    trigram: str
    direction: str
    element: str
    earth_stem: str
    earth_hidden_stems: list[str] = field(default_factory=list)
    heaven_stems: list[str] = field(default_factory=list)
    stars: list[str] = field(default_factory=list)
    door: str | None = None
    deity: str | None = None
    is_void: bool = False
    is_horse: bool = False
    notes: list[str] = field(default_factory=list)


@dataclass
class QimenBoard:
    method: MethodConfig
    calendar: CalendarContext
    dun: str
    yuan: str
    ju: int
    ju_label: str
    fu_head_day: str
    hour_xun: str
    xun_head_instrument: str
    chief_star: str
    chief_door: str
    chief_star_palace: int
    chief_door_palace: int
    void_branches: tuple[str, str]
    horse_branch: str
    horse_palace: int
    palaces: dict[int, PalaceState]
    patterns: list[PatternHit] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["calendar"]["local_datetime"] = self.calendar.local_datetime.isoformat()
        payload["calendar"]["solar_term_at"] = self.calendar.solar_term_at.isoformat()
        payload["calendar"]["next_solar_term_at"] = self.calendar.next_solar_term_at.isoformat()
        payload["generated_at"] = self.generated_at.isoformat()
        payload["palaces"] = {str(key): value for key, value in payload["palaces"].items()}
        return payload
