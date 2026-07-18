from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from version import CALCULATION_VERSION, INPUT_PROTOCOL_VERSION


@dataclass(slots=True)
class CastingInput:
    """Text-count input for a deterministic Meihua casting."""

    title: str
    body_name: str
    use_name: str
    body_text: str
    use_text: str
    full_text: str
    category: str = "足球賽前內容"
    context_notes: str = ""
    scope: str = "只使用賽前資訊，判斷九十分鐘；完整排卦與卦義資料，不自動預測"
    input_protocol_version: str = INPUT_PROTOCOL_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class CastingMoment:
    """Immutable timestamp captured when the casting is calculated."""

    timezone: str
    utc_offset: str
    gregorian_iso: str
    gregorian_text: str
    lunar_text: str
    lunar_year: int
    lunar_year_chinese: str
    lunar_year_ganzhi: str
    lunar_month: int
    lunar_month_text: str
    lunar_is_leap_month: bool
    lunar_day: int
    lunar_day_text: str
    day_ganzhi: str
    day_stem: str
    day_branch: str
    shichen: str
    shichen_ganzhi: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class HexagramResult:
    casting_moment: CastingMoment
    title: str
    body_name: str
    use_name: str
    body_count: int
    use_count: int
    total_count: int
    body_modulo: int
    use_modulo: int
    moving_modulo: int
    body_gua: str
    use_gua: str
    body_number: int
    use_number: int
    body_element: str
    use_element: str
    main_hexagram: str
    main_lines_bottom_up: str
    mutual_lower_gua: str
    mutual_upper_gua: str
    mutual_hexagram: str
    mutual_lines_bottom_up: str
    moving_line: int
    moving_line_label: str
    moving_original_type: str
    moving_changed_type: str
    moving_side: str
    moving_layer: str
    changed_hexagram: str
    changed_lines_bottom_up: str
    changed_body_gua: str
    changed_use_gua: str
    body_transition: str
    use_transition: str
    relation_code: str
    relation: str
    changed_relation_code: str
    changed_relation: str
    line_table: list[dict[str, Any]] = field(default_factory=list)
    calculation_version: str = CALCULATION_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# Compatibility name for old saved notebooks; the active application uses CastingInput.
MatchInput = CastingInput


__all__ = ["CastingInput", "CastingMoment", "HexagramResult", "MatchInput"]
