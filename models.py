from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from version import CALCULATION_VERSION


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
    scope: str = "只排卦，不解卦"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class HexagramResult:
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


__all__ = ["CastingInput", "HexagramResult", "MatchInput"]
