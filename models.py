from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from version import CALCULATION_VERSION, DELIBERATION_VERSION, RULE_VERSION, SCRIPT_VERSION


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
    # 純賽前足球先驗，不參與起卦字數。50/50 表示完全中性。
    body_strength_rating: float = 50.0
    use_strength_rating: float = 50.0
    prior_confidence: float = 0.50
    venue: str = "中立場"

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
    calculation_version: str = CALCULATION_VERSION
    changed_body_number: int = 0
    changed_use_number: int = 0
    changed_body_element: str = ""
    changed_use_element: str = ""
    changed_relation_code: str = ""
    changed_relation: str = ""
    changed_relation_detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class HexagramScript:
    environment: str
    trajectory: str
    opening_reading: str
    middle_reading: str
    ending_reading: str
    energy_flow_summary: str
    dynamics_score: float
    scoring_channel_score: float
    closure_score: float
    volatility_score: float
    body_ownership: float
    use_ownership: float
    body_finishing: float
    use_finishing: float
    mirror_mode: str
    high_score_gate: bool
    zero_goal_gate: bool
    btts_signal: bool
    rout_side: str
    one_sided_side: str
    total_goal_targets: list[int]
    semantic_story: str = ""
    primary_interpretation: str = ""
    counter_interpretation: str = ""
    body_scoring_path: str = ""
    use_scoring_path: str = ""
    turning_point: str = ""
    ending_logic: str = ""
    semantic_evidence: list[dict[str, Any]] = field(default_factory=list)
    scenario_hypotheses: list[dict[str, Any]] = field(default_factory=list)
    numeric_signals: list[dict[str, Any]] = field(default_factory=list)
    candidate_scores: list[dict[str, Any]] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    script_weight: float = 0.0
    version: str = SCRIPT_VERSION

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
    outcome_probabilities: dict[str, float] = field(default_factory=dict)
    diagnostics: list[str] = field(default_factory=list)
    football_prior: dict[str, Any] = field(default_factory=dict)
    football_only_scores: list[tuple[int, int]] = field(default_factory=list)
    football_only_outcome_probabilities: dict[str, float] = field(default_factory=dict)
    football_expected_body_goals: float = 0.0
    football_expected_use_goals: float = 0.0
    hexagram_body_multiplier: float = 1.0
    hexagram_use_multiplier: float = 1.0
    hexagram_adjustment_cap: float = 0.25
    hexagram_script: dict[str, Any] = field(default_factory=dict)
    scenario_weight: float = 0.0
    scenario_expected_body_goals: float = 0.0
    scenario_expected_use_goals: float = 0.0
    method: str = RULE_VERSION

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["scores"] = [list(x) for x in self.scores]
        data["football_only_scores"] = [list(x) for x in self.football_only_scores]
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
    # v4.2：保存盲解語義與足球決策兩層，避免數值結論倒灌第一階段。
    body_strength_score: float = 50.0
    use_strength_score: float = 50.0
    evidence_quality: float = 0.0
    direction_confidence: float = 0.0
    football_evidence: list[str] = field(default_factory=list)
    hexagram_evidence: list[str] = field(default_factory=list)
    contradiction_warning: str = ""
    match_script_summary: str = ""
    opening_phase: str = ""
    middle_phase: str = ""
    ending_phase: str = ""
    scoring_channel_analysis: str = ""
    energy_ownership_analysis: str = ""
    total_goals_reasoning: str = ""
    score_allocation_reasoning: str = ""
    hexagram_deliberation: dict[str, Any] = field(default_factory=dict)
    selected_scenario_names: list[str] = field(default_factory=list)
    deliberation_version: str = DELIBERATION_VERSION

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["scores"] = [list(x) for x in self.scores]
        return data
