from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Mapping

import requests

from ai_reasoner_v32 import run_postmatch_calibration, run_postmatch_calibration_from_row
from evaluation import candidate_scores, outcome, score_tuple
from knowledge_loader import load_hexagrams, load_trigrams
from models import AIAnalysis, HexagramResult, MatchInput, RulePrediction, SimilarCase
from version import DELIBERATION_VERSION, PROMPT_VERSION


GITHUB_MODELS_ENDPOINT = "https://models.github.ai/inference/chat/completions"
GITHUB_MODELS_CATALOG = "https://models.github.ai/catalog/models"
GITHUB_MODELS_API_VERSION = "2026-03-10"
DELIBERATION_SCHEMA: dict[str, Any] = {
    "name": "meihua_blind_hexagram_deliberation_v1",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "thesis": {"type": "string"},
            "primary_conflict": {"type": "string"},
            "opening_phase": {"type": "string"},
            "middle_phase": {"type": "string"},
            "turning_point": {"type": "string"},
            "ending_phase": {"type": "string"},
            "body_agency": {"type": "string"},
            "use_agency": {"type": "string"},
            "body_scoring_path": {"type": "string"},
            "use_scoring_path": {"type": "string"},
            "energy_flow": {"type": "string"},
            "closure_analysis": {"type": "string"},
            "timing_analysis": {"type": "string"},
            "mirror_or_resonance": {"type": "string"},
            "numeric_symbolism": {
                "type": "array",
                "maxItems": 4,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "symbol": {"type": "string"},
                        "supported_meaning": {"type": "string"},
                        "rejected_shortcut": {"type": "string"},
                    },
                    "required": ["symbol", "supported_meaning", "rejected_shortcut"],
                },
            },
            "primary_scenario": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "name": {"type": "string"},
                    "narrative": {"type": "string"},
                    "requires": {"type": "array", "items": {"type": "string"}, "maxItems": 6},
                    "failure_condition": {"type": "string"},
                    "goal_shape": {"type": "string"},
                },
                "required": ["name", "narrative", "requires", "failure_condition", "goal_shape"],
            },
            "alternative_scenario": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "name": {"type": "string"},
                    "narrative": {"type": "string"},
                    "requires": {"type": "array", "items": {"type": "string"}, "maxItems": 6},
                    "failure_condition": {"type": "string"},
                    "goal_shape": {"type": "string"},
                },
                "required": ["name", "narrative", "requires", "failure_condition", "goal_shape"],
            },
            "counter_reading": {"type": "string"},
            "uncertainty_factors": {"type": "array", "items": {"type": "string"}, "maxItems": 8},
            "prohibited_shortcuts": {"type": "array", "items": {"type": "string"}, "maxItems": 8},
        },
        "required": [
            "thesis",
            "primary_conflict",
            "opening_phase",
            "middle_phase",
            "turning_point",
            "ending_phase",
            "body_agency",
            "use_agency",
            "body_scoring_path",
            "use_scoring_path",
            "energy_flow",
            "closure_analysis",
            "timing_analysis",
            "mirror_or_resonance",
            "numeric_symbolism",
            "primary_scenario",
            "alternative_scenario",
            "counter_reading",
            "uncertainty_factors",
            "prohibited_shortcuts",
        ],
    },
}
PREDICTION_SCHEMA: dict[str, Any] = {
    "name": "meihua_football_prediction_v42",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "result_direction": {"type": "string"},
            "direction_confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "evidence_quality": {"type": "number", "minimum": 0, "maximum": 1},
            "body_strength_score": {"type": "number", "minimum": 0, "maximum": 100},
            "use_strength_score": {"type": "number", "minimum": 0, "maximum": 100},
            "football_evidence": {"type": "array", "items": {"type": "string"}, "maxItems": 8},
            "hexagram_evidence": {"type": "array", "items": {"type": "string"}, "maxItems": 8},
            "contradiction_warning": {"type": "string"},
            "match_script_summary": {"type": "string"},
            "opening_phase": {"type": "string"},
            "middle_phase": {"type": "string"},
            "ending_phase": {"type": "string"},
            "scoring_channel_analysis": {"type": "string"},
            "energy_ownership_analysis": {"type": "string"},
            "total_goals_reasoning": {"type": "string"},
            "score_allocation_reasoning": {"type": "string"},
            "selected_scenario_names": {
                "type": "array",
                "minItems": 1,
                "maxItems": 3,
                "items": {"type": "string"},
            },
            "score_candidates": {
                "type": "array",
                "minItems": 3,
                "maxItems": 3,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "score": {"type": "string"},
                        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                        "reason": {"type": "string"},
                    },
                    "required": ["score", "confidence", "reason"],
                },
            },
            "overall_reasoning": {"type": "string"},
            "risk_warning": {"type": "string"},
            "similar_case_analysis": {
                "type": "array",
                "maxItems": 8,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "case_id": {"type": "string"},
                        "usable_lesson": {"type": "string"},
                        "important_difference": {"type": "string"},
                    },
                    "required": ["case_id", "usable_lesson", "important_difference"],
                },
            },
            "calibration_suggestions": {"type": "array", "items": {"type": "string"}, "maxItems": 8},
            "used_case_ids": {"type": "array", "items": {"type": "string"}, "maxItems": 10},
        },
        "required": [
            "result_direction",
            "direction_confidence",
            "evidence_quality",
            "body_strength_score",
            "use_strength_score",
            "football_evidence",
            "hexagram_evidence",
            "contradiction_warning",
            "match_script_summary",
            "opening_phase",
            "middle_phase",
            "ending_phase",
            "scoring_channel_analysis",
            "energy_ownership_analysis",
            "total_goals_reasoning",
            "score_allocation_reasoning",
            "selected_scenario_names",
            "score_candidates",
            "overall_reasoning",
            "risk_warning",
            "similar_case_analysis",
            "calibration_suggestions",
            "used_case_ids",
        ],
    },
}


class GitHubModelsError(RuntimeError):
    pass


@dataclass(slots=True)
class GitHubModelsClient:
    token: str
    model: str
    timeout: int = 45
    max_tokens: int = 3200
    temperature: float = 0.1

    def _headers(self) -> dict[str, str]:
        return {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self.token}",
            "X-GitHub-Api-Version": GITHUB_MODELS_API_VERSION,
            "Content-Type": "application/json",
        }

    def list_models(self) -> list[dict[str, Any]]:
        response = requests.get(GITHUB_MODELS_CATALOG, headers=self._headers(), timeout=self.timeout)
        self._raise_for_status(response)
        payload = response.json()
        return payload if isinstance(payload, list) else []

    def infer_json(
        self,
        system_prompt: str,
        user_prompt: str,
        json_schema: Mapping[str, Any] | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        schema = dict(json_schema or PREDICTION_SCHEMA)
        base_body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "stream": False,
        }
        attempts = [
            {**base_body, "response_format": {"type": "json_schema", "json_schema": schema}},
            {**base_body, "response_format": {"type": "json_object"}},
            base_body,
        ]
        last_response: requests.Response | None = None
        for body in attempts:
            response = requests.post(
                GITHUB_MODELS_ENDPOINT,
                headers=self._headers(),
                json=body,
                timeout=self.timeout,
            )
            last_response = response
            if response.status_code not in {400, 422}:
                break
        if last_response is None:
            raise GitHubModelsError("GitHub Models 未產生回應")
        self._raise_for_status(last_response)
        payload = last_response.json()
        try:
            content = payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise GitHubModelsError("GitHub Models 回應缺少 choices[0].message.content") from exc
        return _parse_json_object(str(content)), payload

    def infer_json_object(self, system_prompt: str, user_prompt: str) -> tuple[dict[str, Any], dict[str, Any]]:
        """Request generic JSON for post-match tasks that use a different schema."""
        base_body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "stream": False,
        }
        last_response: requests.Response | None = None
        for body in [{**base_body, "response_format": {"type": "json_object"}}, base_body]:
            response = requests.post(
                GITHUB_MODELS_ENDPOINT,
                headers=self._headers(),
                json=body,
                timeout=self.timeout,
            )
            last_response = response
            if response.status_code not in {400, 422}:
                break
        if last_response is None:
            raise GitHubModelsError("GitHub Models 未產生回應")
        self._raise_for_status(last_response)
        payload = last_response.json()
        try:
            content = payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise GitHubModelsError("GitHub Models 回應缺少 choices[0].message.content") from exc
        return _parse_json_object(str(content)), payload

    @staticmethod
    def _raise_for_status(response: requests.Response) -> None:
        if response.ok:
            return
        try:
            payload = response.json()
            message = payload.get("message") or payload.get("error", {}).get("message") or str(payload)
        except Exception:
            message = response.text[:500]
        hints = {
            401: "Token無效或已過期。",
            403: "Token可能缺少Models: Read-only，或模型未對帳號開放。",
            404: "模型ID可能不存在。",
            429: "免費額度或速率限制已達上限；系統會退回本地規則引擎。",
        }
        hint = hints.get(response.status_code, "GitHub Models服務暫時異常。" if response.status_code >= 500 else "請查看Streamlit log。")
        raise GitHubModelsError(f"GitHub Models HTTP {response.status_code}: {message} {hint}".strip())


def _parse_json_object(content: str) -> dict[str, Any]:
    cleaned = content.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start >= 0 and end > start:
        try:
            parsed = json.loads(cleaned[start : end + 1])
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError as exc:
            raise GitHubModelsError(f"AI回傳JSON無法解析：{exc}") from exc
    raise GitHubModelsError("AI沒有回傳有效JSON物件")


def _truncate(text: str, limit: int) -> str:
    text = (text or "").strip()
    return text if len(text) <= limit else text[:limit] + "…"


def _clamp_float(value: Any, low: float, high: float, default: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = default
    return max(low, min(high, number))


EXACT_SCORE_PATTERN = re.compile(r"(?<!\d)\d{1,2}\s*[-:：–—]\s*\d{1,2}(?!\d)")


def _strip_exact_scores(value: Any) -> str:
    text = str(value or "").strip()
    return EXACT_SCORE_PATTERN.sub("（精確比分留待第二階段）", text)


def _string_list(value: Any, limit: int = 8) -> list[str]:
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        return []
    return [_strip_exact_scores(item) for item in value if _strip_exact_scores(item)][:limit]


def _scenario(value: Any, fallback: Mapping[str, Any]) -> dict[str, Any]:
    source = value if isinstance(value, Mapping) else fallback
    return {
        "name": _strip_exact_scores(source.get("name", fallback.get("name", "替代劇本"))),
        "narrative": _strip_exact_scores(source.get("narrative", fallback.get("narrative", ""))),
        "requires": _string_list(source.get("requires", fallback.get("requires", [])), 6),
        "failure_condition": _strip_exact_scores(
            source.get("failure_condition", fallback.get("failure_condition", ""))
        ),
        "goal_shape": _strip_exact_scores(source.get("goal_shape", fallback.get("goal_shape", ""))),
    }


def _deterministic_deliberation(rule_prediction: RulePrediction) -> dict[str, Any]:
    script = rule_prediction.hexagram_script or {}
    scenarios = script.get("scenario_hypotheses", [])
    if not isinstance(scenarios, list):
        scenarios = []
    primary = scenarios[0] if scenarios and isinstance(scenarios[0], Mapping) else {}
    alternative = scenarios[1] if len(scenarios) > 1 and isinstance(scenarios[1], Mapping) else {}
    numeric_symbolism = []
    for signal in script.get("numeric_signals", []):
        if not isinstance(signal, Mapping):
            continue
        numeric_symbolism.append(
            {
                "symbol": str(signal.get("formula", "卦數條件")),
                "supported_meaning": str(signal.get("reason", "只作次級總量錨點")),
                "rejected_shortcut": "卦數不能直接當成任一方進球，也不能為配合已知結果任選公式。",
            }
        )
    evidence = script.get("semantic_evidence", [])
    primary_conflict = ""
    if isinstance(evidence, list) and evidence and isinstance(evidence[0], Mapping):
        primary_conflict = str(evidence[0].get("observation", ""))
    return {
        "thesis": str(script.get("primary_interpretation", script.get("semantic_story", ""))),
        "primary_conflict": primary_conflict,
        "opening_phase": str(script.get("opening_reading", "")),
        "middle_phase": str(script.get("middle_reading", "")),
        "turning_point": str(script.get("turning_point", script.get("ending_reading", ""))),
        "ending_phase": str(script.get("ending_logic", script.get("ending_reading", ""))),
        "body_agency": str(script.get("body_scoring_path", "")),
        "use_agency": str(script.get("use_scoring_path", "")),
        "body_scoring_path": str(script.get("body_scoring_path", "")),
        "use_scoring_path": str(script.get("use_scoring_path", "")),
        "energy_flow": str(script.get("energy_flow_summary", "")),
        "closure_analysis": str(script.get("primary_interpretation", "")),
        "timing_analysis": str(script.get("turning_point", "")),
        "mirror_or_resonance": str(script.get("mirror_mode", "無同數結構")),
        "numeric_symbolism": numeric_symbolism[:4],
        "primary_scenario": primary,
        "alternative_scenario": alternative,
        "counter_reading": str(script.get("counter_interpretation", "")),
        "uncertainty_factors": [
            "語義劇本仍需由賽前足球強弱與陣容資料校準。",
            "動爻表示轉折窗口，不保證轉象一定轉成實際進球。",
        ],
        "prohibited_shortcuts": [
            "不得把單一體用生剋直接當勝負。",
            "不得把卦數直接當進球。",
            "不得把高動能直接當高比分。",
        ],
    }


def _validate_deliberation(data: Any, fallback: Mapping[str, Any]) -> dict[str, Any]:
    source = data if isinstance(data, Mapping) else {}
    normalized: dict[str, Any] = {}
    string_fields = [
        "thesis",
        "primary_conflict",
        "opening_phase",
        "middle_phase",
        "turning_point",
        "ending_phase",
        "body_agency",
        "use_agency",
        "body_scoring_path",
        "use_scoring_path",
        "energy_flow",
        "closure_analysis",
        "timing_analysis",
        "mirror_or_resonance",
        "counter_reading",
    ]
    for field in string_fields:
        normalized[field] = _strip_exact_scores(source.get(field, fallback.get(field, "")))

    raw_numeric = source.get("numeric_symbolism", fallback.get("numeric_symbolism", []))
    numeric: list[dict[str, str]] = []
    if isinstance(raw_numeric, list):
        for item in raw_numeric:
            if not isinstance(item, Mapping):
                continue
            numeric.append(
                {
                    "symbol": _strip_exact_scores(item.get("symbol", "")),
                    "supported_meaning": _strip_exact_scores(item.get("supported_meaning", "")),
                    "rejected_shortcut": _strip_exact_scores(item.get("rejected_shortcut", "")),
                }
            )
    normalized["numeric_symbolism"] = numeric[:4]
    normalized["primary_scenario"] = _scenario(
        source.get("primary_scenario"),
        fallback.get("primary_scenario", {}),
    )
    normalized["alternative_scenario"] = _scenario(
        source.get("alternative_scenario"),
        fallback.get("alternative_scenario", {}),
    )
    normalized["uncertainty_factors"] = _string_list(
        source.get("uncertainty_factors", fallback.get("uncertainty_factors", [])),
        8,
    )
    normalized["prohibited_shortcuts"] = _string_list(
        source.get("prohibited_shortcuts", fallback.get("prohibited_shortcuts", [])),
        8,
    )
    normalized["version"] = DELIBERATION_VERSION
    normalized["blind_to_scores"] = True
    return normalized


def build_deliberation_prompt(
    match: MatchInput,
    result: HexagramResult,
    rule_prediction: RulePrediction,
) -> tuple[str, str]:
    trigrams = load_trigrams()
    hexagrams = load_hexagrams()
    semantic_trigram_keys = {
        "number",
        "element",
        "yin_yang",
        "lines",
        "symbol",
        "nature",
        "football",
        "attack",
        "defense",
        "tempo",
        "goal_rule",
        "tags",
    }
    involved_trigrams = {
        name: {
            key: value
            for key, value in trigrams[name].items()
            if key in semantic_trigram_keys
        }
        for name in {result.body_gua, result.use_gua, result.changed_body_gua, result.changed_use_gua}
    }
    semantic_hexagram_keys = {
        "sequence",
        "upper",
        "lower",
        "core",
        "football",
        "opening",
        "middle",
        "ending",
        "body_reading",
        "use_reading",
        "risk",
        "tags",
    }
    involved_hexagrams = {
        name: {
            key: value
            for key, value in hexagrams[name].items()
            if key in semantic_hexagram_keys
        }
        for name in {result.main_hexagram, result.mutual_hexagram, result.changed_hexagram}
    }
    script = rule_prediction.hexagram_script or {}
    scaffold_evidence = [
        item
        for item in script.get("semantic_evidence", [])
        if isinstance(item, Mapping) and item.get("stage") != "同異結構"
    ]
    qualitative_scaffold = {
        "body_scoring_path": script.get("body_scoring_path", ""),
        "use_scoring_path": script.get("use_scoring_path", ""),
        "turning_point": script.get("turning_point", ""),
        "ending_logic": script.get("ending_logic", ""),
        "source_evidence_without_quantitative_conclusion": scaffold_evidence,
    }
    immutable_blind_result = {
        key: value
        for key, value in result.to_dict().items()
        if key
        in {
            "match_name",
            "body_team",
            "use_team",
            "body_gua",
            "use_gua",
            "body_number",
            "use_number",
            "body_element",
            "use_element",
            "main_hexagram",
            "mutual_hexagram",
            "moving_line",
            "moving_side",
            "moving_layer",
            "changed_hexagram",
            "changed_body_gua",
            "changed_use_gua",
            "changed_body_number",
            "changed_use_number",
            "changed_body_element",
            "changed_use_element",
            "body_transition",
            "use_transition",
            "relation_code",
            "relation",
            "relation_detail",
            "changed_relation_code",
            "changed_relation",
            "changed_relation_detail",
            "moving_detail",
        }
    }
    system_prompt = f"""
你是「梅花易數足球盲解卦AI」，版本{DELIBERATION_VERSION}。這是第一階段：只做語義推演，完全不能看比分候選、機率、λ、實力分或規則排名。你的工作不是計算，而是把卦讀成一場有先後、角色、因果與反證的比賽。

硬性規則：
1. 只使用提供的賽前資料，只談90分鐘，不含延長賽與PK；不得使用本場實際結果或模型記憶中的賽果。
2. Python算出的體、用、本卦、互卦、動爻、轉象與變卦不可更改。
3. 必須沿「本卦主局 → 互卦內部發展 → 動爻事件與時間窗口 → 變卦終局」逐段推演，不得把卦義拆成互不相干的標籤。
4. 每個結論必須說明由哪一卦、哪一方、哪個轉象或哪段五行關係支持。
5. 必須同時寫主解與反解，並清楚列出各自成立條件；艮、坤、剝、乾等多義象不能依想要的答案任選含義。
6. 必須把場面動能、真實破門通道、能量歸屬、終局收束與動方自身成果分開思考。
7. 動爻時間必須影響幅度：初爻可影響較長，上爻只能形成較晚的追擊、守成或決勝。
8. 卦數只能談象徵與受限數路，必須寫出「它支持什麼」和「它不能證明什麼」。
9. 本階段禁止輸出任何精確比分、候選比分、比分區間、勝率、機率、λ、實力分或最終投注式結論；也禁止以任何比分格式偷渡答案。
10. 不得照抄 qualitative_scaffold；要審查它、指出哪裡可能有另一種合理解讀。
11. 只輸出符合JSON Schema的物件。
""".strip()
    user_payload = {
        "phase": "blind_semantic_hexagram_deliberation",
        "current_match_context_without_numeric_prior": {
            "match_name": match.match_name,
            "competition": match.competition,
            "scope": match.scope,
            "body_team": match.body_team,
            "use_team": match.use_team,
            "prematch_leaning_only_sets_body_use": match.prematch_leaning,
            "body_prematch_text": _truncate(match.body_text, 1800),
            "use_prematch_text": _truncate(match.use_text, 1800),
            "neutral_prematch_text": _truncate(match.full_text, 3600),
            "context_notes": _truncate(match.context_notes, 1400),
        },
        "immutable_hexagram_result": immutable_blind_result,
        "trigram_semantics": involved_trigrams,
        "hexagram_semantics": involved_hexagrams,
        "deterministic_qualitative_scaffold_to_review": qualitative_scaffold,
        "required_reasoning_order": [
            "定義本卦的核心矛盾與體用角色",
            "說明互卦如何在主局內部發展",
            "判斷動方自身得到或失去什麼，並套用爻位時間窗口",
            "比較原始與變卦五行關係是否延續、洩漏或反轉",
            "分別描述兩方實際破門路徑與收束機制",
            "提出主劇本、替代劇本、反證與不確定性",
            "最後才討論受限卦數象徵，但仍不產生比分",
        ],
    }
    return system_prompt, json.dumps(user_payload, ensure_ascii=False, separators=(",", ":"))


def _validate_ai_analysis(
    data: dict[str, Any],
    rule_prediction: RulePrediction,
    provider: str,
    model: str,
    raw_response: dict[str, Any],
    deliberation: Mapping[str, Any] | None = None,
) -> AIAnalysis:
    allowed = candidate_scores(rule_prediction, 18)
    allowed_set = set(allowed)
    candidates = data.get("score_candidates", [])
    if not isinstance(candidates, list):
        candidates = []

    scores: list[tuple[int, int]] = []
    confidences: list[float] = []
    score_reasons: list[str] = []
    for item in candidates:
        if not isinstance(item, dict):
            continue
        score = score_tuple(str(item.get("score", "")))
        if score is None or score not in allowed_set or score in scores:
            continue
        scores.append(score)
        confidences.append(_clamp_float(item.get("confidence"), 0.0, 1.0, 0.0))
        score_reasons.append(str(item.get("reason", "")).strip())
        if len(scores) == 3:
            break

    for score in allowed:
        if len(scores) == 3:
            break
        if score not in scores:
            scores.append(score)
            confidences.append(0.0)
            score_reasons.append("AI輸出不足，沿用平衡候選池順位。")

    first_direction = outcome(f"{scores[0][0]}-{scores[0][1]}") if scores else rule_prediction.direction
    requested_direction = str(data.get("result_direction", "")).strip()
    direction = requested_direction if requested_direction in {"體方勝", "平局", "用方勝", "一球差拉鋸"} else first_direction

    similar_case_analysis = data.get("similar_case_analysis", [])
    if not isinstance(similar_case_analysis, list):
        similar_case_analysis = []
    suggestions = data.get("calibration_suggestions", [])
    if isinstance(suggestions, str):
        suggestions = [suggestions]
    if not isinstance(suggestions, list):
        suggestions = []
    used_ids = data.get("used_case_ids", [])
    if isinstance(used_ids, str):
        used_ids = [used_ids]
    if not isinstance(used_ids, list):
        used_ids = []
    football_evidence = data.get("football_evidence", [])
    if not isinstance(football_evidence, list):
        football_evidence = []
    hexagram_evidence = data.get("hexagram_evidence", [])
    if not isinstance(hexagram_evidence, list):
        hexagram_evidence = []
    selected_scenarios = data.get("selected_scenario_names", [])
    if not isinstance(selected_scenarios, list):
        selected_scenarios = []

    return AIAnalysis(
        ok=True,
        provider=provider,
        model=model,
        direction=direction,
        scores=scores[:3],
        confidences=confidences[:3],
        score_reasons=score_reasons[:3],
        overall_reasoning=str(data.get("overall_reasoning", "")).strip(),
        risk_warning=str(data.get("risk_warning", "")).strip(),
        similar_case_analysis=[x for x in similar_case_analysis if isinstance(x, dict)][:8],
        calibration_suggestions=[str(x).strip() for x in suggestions if str(x).strip()][:8],
        used_case_ids=[str(x).strip() for x in used_ids if str(x).strip()][:10],
        raw_response=raw_response,
        body_strength_score=_clamp_float(data.get("body_strength_score"), 0.0, 100.0, 50.0),
        use_strength_score=_clamp_float(data.get("use_strength_score"), 0.0, 100.0, 50.0),
        evidence_quality=_clamp_float(data.get("evidence_quality"), 0.0, 1.0, 0.0),
        direction_confidence=_clamp_float(data.get("direction_confidence"), 0.0, 1.0, 0.0),
        football_evidence=[str(x).strip() for x in football_evidence if str(x).strip()][:8],
        hexagram_evidence=[str(x).strip() for x in hexagram_evidence if str(x).strip()][:8],
        contradiction_warning=str(data.get("contradiction_warning", "")).strip(),
        match_script_summary=str(data.get("match_script_summary", "")).strip(),
        opening_phase=str(data.get("opening_phase", "")).strip(),
        middle_phase=str(data.get("middle_phase", "")).strip(),
        ending_phase=str(data.get("ending_phase", "")).strip(),
        scoring_channel_analysis=str(data.get("scoring_channel_analysis", "")).strip(),
        energy_ownership_analysis=str(data.get("energy_ownership_analysis", "")).strip(),
        total_goals_reasoning=str(data.get("total_goals_reasoning", "")).strip(),
        score_allocation_reasoning=str(data.get("score_allocation_reasoning", "")).strip(),
        hexagram_deliberation=dict(deliberation or {}),
        selected_scenario_names=[str(item).strip() for item in selected_scenarios if str(item).strip()][:3],
        deliberation_version=str((deliberation or {}).get("version", DELIBERATION_VERSION)),
    )


def _decision_candidate_pool(rule_prediction: RulePrediction) -> list[dict[str, Any]]:
    allowed = candidate_scores(rule_prediction, 18)
    grid = {
        str(row.get("score", "")): row
        for row in rule_prediction.score_grid
        if isinstance(row, Mapping)
    }
    script = rule_prediction.hexagram_script or {}
    script_candidates = {
        str(item.get("score", "")): item
        for item in script.get("candidate_scores", [])
        if isinstance(item, Mapping)
    }
    output: list[dict[str, Any]] = []
    for body, use in sorted(allowed, key=lambda score: (sum(score), abs(score[0] - score[1]), score[0], score[1])):
        score = f"{body}-{use}"
        row = grid.get(score, {})
        base_probability = _clamp_float(row.get("base_probability", row.get("probability")), 0.0, 1.0, 0.0)
        if base_probability >= 0.08:
            football_support = "高"
        elif base_probability >= 0.03:
            football_support = "中"
        else:
            football_support = "低／尾部"
        archetype = script_candidates.get(score, {})
        output.append(
            {
                "score": score,
                "outcome": outcome(score),
                "total_goals": body + use,
                "football_support_band": football_support,
                "script_archetype": str(archetype.get("archetype", "一般網格候選")),
                "script_reason": str(archetype.get("reason", "")),
            }
        )
    return output


def build_prediction_prompt(
    match: MatchInput,
    result: HexagramResult,
    rule_prediction: RulePrediction,
    similar_cases: list[SimilarCase],
    deliberation: Mapping[str, Any] | None = None,
) -> tuple[str, str]:
    blind_deliberation = dict(deliberation or _validate_deliberation(
        {},
        _deterministic_deliberation(rule_prediction),
    ))
    script = rule_prediction.hexagram_script or {}
    candidate_pool = _decision_candidate_pool(rule_prediction)
    applied_rules = [
        {
            "id": rule.get("id", ""),
            "name": rule.get("name", ""),
            "status": rule.get("status", ""),
            "applied": bool(rule.get("applied", False)),
            "applied_scale": rule.get("applied_scale", 0.0),
            **(
                {
                    "conditions": rule.get("conditions", {}),
                    "lesson": rule.get("lesson", ""),
                }
                if rule.get("applied")
                else {}
            ),
        }
        for rule in rule_prediction.matched_rules
    ]
    case_payload = [
        {
            "case_id": case.case_id,
            "match": case.match_name,
            "similarity": case.similarity,
            "common_points": case.common_points,
            "important_differences": case.differences,
            "historical_prediction": case.predicted_scores,
            "historical_actual_score": case.actual_score,
            "calibration_reason": _truncate(case.calibration_reason, 650),
            "lesson_summary": _truncate(case.lesson_summary, 450),
        }
        for case in similar_cases
    ]
    system_prompt = f"""
你是「梅花易數足球語義決策AI」，版本{PROMPT_VERSION}。這是第二階段。第一階段已在完全看不到比分、機率與λ的情況下完成 blind_hexagram_deliberation；你現在才可以用足球先驗校準它，選擇劇本、總球形狀與精確比分。

不可違反：
1. 只使用提供的賽前資料，只判90分鐘，不含延長賽與PK；不得使用或猜測本場賽後結果。
2. Python固定卦象與第一階段盲解不得悄悄改寫。若你不同意盲解，必須在contradiction_warning指出具體反證，不能只用數字覆蓋語義。
3. 決策順序固定為：選劇本 → 檢查足球反證 → 判總球形狀 → 判兩方破門路徑 → 最後才選比分。
4. selected_scenario_names要先列出實際採用的盲解劇本；每個比分理由必須追溯到劇本名稱、哪方破門通道與足球先驗。
5. 候選池以中性順序提供，沒有暗示排名。football_support_band只表示Poisson可行性，不是答案；script_archetype也不是必選。
6. 高動能不等於高比分，收束也不是一票否決。必須說明真實破門通道是否存在、屬於誰、能否重複。
7. 同卦同數不可固定判平或固定大球；卦數只作受限次級錨點，不得直接當進球。
8. 支持隊只決定體方，不替體方實力加分。足球實力只能採提供的賽前資料。
9. 只能從allowed_score_candidates選3個互不相同的比分，不可自創池外比分，也不可因常見而習慣性選1-1或2-1。
10. 歷史案例只提供可泛化教訓，不可直接複製舊比分；未通過留出驗證的單場假說不得增加權重。
11. 證據不足時降低evidence_quality與direction_confidence，並在risk_warning保留替代劇本。
12. match_script_summary必須把盲解劇本與足球校準串成一段有因果的敘事；其他階段欄位不得重複同一句套話。
13. 只輸出符合JSON Schema的物件。
""".strip()
    user_payload = {
        "phase": "football_calibration_and_score_decision",
        "current_match": {
            "match_name": match.match_name,
            "competition": match.competition,
            "scope": match.scope,
            "body_team": match.body_team,
            "use_team": match.use_team,
            "prematch_leaning_only_sets_body_use": match.prematch_leaning,
            "body_prematch_text": _truncate(match.body_text, 1800),
            "use_prematch_text": _truncate(match.use_text, 1800),
            "neutral_prematch_text": _truncate(match.full_text, 3600),
            "context_notes": _truncate(match.context_notes, 1400),
        },
        "blind_hexagram_deliberation": blind_deliberation,
        "football_prior": {
            "body_strength_rating": match.body_strength_rating,
            "use_strength_rating": match.use_strength_rating,
            "prior_confidence": match.prior_confidence,
            "venue": match.venue,
            "body_lambda": rule_prediction.football_expected_body_goals,
            "use_lambda": rule_prediction.football_expected_use_goals,
        },
        "bounded_hexagram_adjustment": {
            "body_multiplier": rule_prediction.hexagram_body_multiplier,
            "use_multiplier": rule_prediction.hexagram_use_multiplier,
            "cap": rule_prediction.hexagram_adjustment_cap,
            "adjusted_body_lambda": rule_prediction.expected_body_goals,
            "adjusted_use_lambda": rule_prediction.expected_use_goals,
        },
        "qualitative_script_constraints": {
            "environment": script.get("environment", ""),
            "mirror_mode": script.get("mirror_mode", ""),
            "zero_goal_gate": script.get("zero_goal_gate", False),
            "high_score_gate": script.get("high_score_gate", False),
            "btts_signal": script.get("btts_signal", False),
            "rout_side": script.get("rout_side", ""),
            "one_sided_side": script.get("one_sided_side", ""),
            "total_goal_targets": script.get("total_goal_targets", []),
            "numeric_signals": script.get("numeric_signals", []),
            "scenario_hypotheses": script.get("scenario_hypotheses", []),
        },
        "allowed_score_candidates": candidate_pool,
        "applied_rule_audit": applied_rules,
        "confirmed_similar_case_count": len(similar_cases),
        "retrieved_historical_cases": case_payload,
        "decision_protocol": [
            "引用blind_hexagram_deliberation選出主劇本與替代劇本",
            "用足球先驗檢查主劇本是否需縮小、放大或改變能量歸屬",
            "先決定總球形狀與雙方是否都有真實破門路徑",
            "再從中性排序候選池選三個能代表主線、鄰近線與風險線的比分",
            "逐一說明每個比分為何符合所選劇本，而不是只引用機率或常見比分",
        ],
    }
    return system_prompt, json.dumps(user_payload, ensure_ascii=False, separators=(",", ":"))


def run_ai_prediction(
    client: GitHubModelsClient,
    match: MatchInput,
    result: HexagramResult,
    rule_prediction: RulePrediction,
    similar_cases: list[SimilarCase],
    deliberation_client: GitHubModelsClient | None = None,
) -> AIAnalysis:
    semantic_client = deliberation_client or client
    fallback = _deterministic_deliberation(rule_prediction)
    deliberation_error = ""
    raw_deliberation: dict[str, Any] = {}
    try:
        semantic_system, semantic_user = build_deliberation_prompt(match, result, rule_prediction)
        semantic_data, raw_deliberation = semantic_client.infer_json(
            semantic_system,
            semantic_user,
            DELIBERATION_SCHEMA,
        )
        deliberation = _validate_deliberation(semantic_data, fallback)
        deliberation["model"] = semantic_client.model
    except Exception as exc:
        deliberation_error = str(exc)
        deliberation = _validate_deliberation({}, fallback)
        deliberation["model"] = "local_semantic_fallback"
        raw_deliberation = {"error": deliberation_error, "fallback": "deterministic_semantic_scaffold"}

    try:
        decision_system, decision_user = build_prediction_prompt(
            match,
            result,
            rule_prediction,
            similar_cases,
            deliberation,
        )
        decision_data, raw_decision = client.infer_json(
            decision_system,
            decision_user,
            PREDICTION_SCHEMA,
        )
        analysis = _validate_ai_analysis(
            decision_data,
            rule_prediction,
            "github_models_two_stage",
            client.model,
            {"deliberation": raw_deliberation, "decision": raw_decision},
            deliberation,
        )
        if deliberation_error:
            warning = "第一階段AI盲解失敗，已用本地語義劇本進入第二階段。"
            analysis.risk_warning = f"{warning}{analysis.risk_warning}".strip()
        return analysis
    except Exception as exc:
        return AIAnalysis(
            ok=False,
            provider="github_models_two_stage",
            model=client.model,
            direction=rule_prediction.direction,
            scores=list(rule_prediction.scores),
            confidences=[0.0, 0.0, 0.0],
            score_reasons=["AI不可用，沿用v4.2本地語義劇本×足球先驗引擎。"] * 3,
            overall_reasoning="",
            risk_warning="",
            error=f"第二階段決策失敗：{exc}",
            raw_response={"deliberation": raw_deliberation},
            hexagram_deliberation=deliberation,
        )
