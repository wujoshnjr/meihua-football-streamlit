from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class MatchInput:
    match_name: str
    body_team: str
    use_team: str
    body_text: str
    use_text: str
    full_text: str
    competition: str = ""
    scope: str = "90分鐘，不含延長賽與PK"
    prematch_leaning: str = ""
    context_notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class HexagramResult:
    match_name: str
    body_team: str
    use_team: str
    body_count: int
    use_count: int
    total_count: int
    body_gua: str
    use_gua: str
    body_number: int
    use_number: int
    body_element: str
    use_element: str
    main_hexagram: str
    mutual_hexagram: str
    moving_line: int
    moving_side: str
    moving_layer: str
    changed_hexagram: str
    changed_body_gua: str
    changed_use_gua: str
    body_transition: str
    use_transition: str
    relation_code: str
    relation: str
    relation_detail: str
    moving_detail: str
    structural_tags: list[str] = field(default_factory=list)
    calculation_version: str = "meihua-engine-v3.1"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class RulePrediction:
    scores: list[tuple[int, int]]
    expected_body_goals: float
    expected_use_goals: float
    direction: str
    confidence: float
    reasons: list[str]
    matched_rules: list[dict[str, Any]] = field(default_factory=list)
    score_grid: list[dict[str, Any]] = field(default_factory=list)
    method: str = "hybrid-rule-engine-v3.1"

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["scores"] = [list(x) for x in self.scores]
        return data


@dataclass(slots=True)
class SimilarCase:
    case_id: str
    match_name: str
    similarity: float
    structural_similarity: float
    text_similarity: float
    actual_score: str
    predicted_scores: str
    calibration_reason: str
    lesson_summary: str
    common_points: list[str] = field(default_factory=list)
    differences: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class AIAnalysis:
    ok: bool
    provider: str
    model: str
    direction: str
    scores: list[tuple[int, int]]
    confidences: list[float]
    score_reasons: list[str]
    overall_reasoning: str
    risk_warning: str
    similar_case_analysis: list[dict[str, Any]] = field(default_factory=list)
    calibration_suggestions: list[str] = field(default_factory=list)
    used_case_ids: list[str] = field(default_factory=list)
    raw_response: dict[str, Any] = field(default_factory=dict)
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["scores"] = [list(x) for x in self.scores]
        return data
