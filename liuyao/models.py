from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class LiuyaoLine:
    position: int
    raw_value: int
    line_kind: str
    yin_yang: str
    moving: bool
    changed_yin_yang: str
    stem: str
    branch: str
    element: str
    relative: str
    six_spirit: str
    is_shi: bool
    is_ying: bool
    is_void: bool
    month_relation: str | None
    day_relation: str | None
    month_break: bool
    day_clash: bool
    changed_stem: str | None = None
    changed_branch: str | None = None
    changed_element: str | None = None
    changed_relative: str | None = None
    changed_relation_to_original: str | None = None
    hidden_relative: str | None = None
    hidden_branch: str | None = None
    hidden_element: str | None = None
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class LiuyaoChart:
    schema_version: str
    method_id: str
    event_local_at: datetime
    timezone_name: str
    month_ganzhi: str
    month_branch: str
    day_ganzhi: str
    day_stem: str
    day_branch: str
    day_xun: str
    void_branches: tuple[str, str]
    original_hexagram: str
    changed_hexagram: str
    original_upper_trigram: str
    original_lower_trigram: str
    changed_upper_trigram: str
    changed_lower_trigram: str
    palace: str
    palace_element: str
    palace_stage: str
    shi_line: int
    ying_line: int
    moving_lines: tuple[int, ...]
    original_is_six_clash: bool
    original_is_six_harmony: bool
    changed_is_six_clash: bool
    changed_is_six_harmony: bool
    six_spirit_start: str
    lines: tuple[LiuyaoLine, ...]
    source_boundary: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["event_local_at"] = self.event_local_at.isoformat()
        return payload


@dataclass(frozen=True)
class LiuyaoQuestionRole:
    schema_version: str
    status: str
    question_category: str
    primary_use: str | None
    secondary_uses: tuple[str, ...] = ()
    rationale: tuple[str, ...] = ()
    authority: str = "SOURCE_AWARE_CATEGORY_MAPPING"
    football_adaptation: dict[str, Any] | None = None


@dataclass(frozen=True)
class LiuyaoReview:
    schema_version: str
    status: str
    chart: dict[str, Any]
    question_role: dict[str, Any] | None
    strength_review: dict[str, Any]
    motion_review: dict[str, Any]
    source_audit: dict[str, Any]
    contradiction_register: list[dict[str, Any]] = field(default_factory=list)
    uncertainty_register: list[dict[str, Any]] = field(default_factory=list)
