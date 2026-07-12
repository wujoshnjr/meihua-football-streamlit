from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

import requests

from ai_reasoner_v32 import run_postmatch_calibration, run_postmatch_calibration_from_row
from evaluation import candidate_scores, outcome, score_tuple
from knowledge_loader import load_hexagrams, load_trigrams
from models import AIAnalysis, HexagramResult, MatchInput, RulePrediction, SimilarCase
from version import PROMPT_VERSION


GITHUB_MODELS_ENDPOINT = "https://models.github.ai/inference/chat/completions"
GITHUB_MODELS_CATALOG = "https://models.github.ai/catalog/models"
GITHUB_MODELS_API_VERSION = "2026-03-10"
PREDICTION_SCHEMA: dict[str, Any] = {
    "name": "meihua_football_prediction_v40",
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
    max_tokens: int = 1800
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

    def infer_json(self, system_prompt: str, user_prompt: str) -> tuple[dict[str, Any], dict[str, Any]]:
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
            {**base_body, "response_format": {"type": "json_schema", "json_schema": PREDICTION_SCHEMA}},
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


def _validate_ai_analysis(
    data: dict[str, Any],
    rule_prediction: RulePrediction,
    provider: str,
    model: str,
    raw_response: dict[str, Any],
) -> AIAnalysis:
    allowed = candidate_scores(rule_prediction, 15)
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
    )


def build_prediction_prompt(
    match: MatchInput,
    result: HexagramResult,
    rule_prediction: RulePrediction,
    similar_cases: list[SimilarCase],
) -> tuple[str, str]:
    trigrams = load_trigrams()
    hexagrams = load_hexagrams()
    involved_trigrams = {
        name: trigrams[name]
        for name in {result.body_gua, result.use_gua, result.changed_body_gua, result.changed_use_gua}
    }
    involved_hexagrams = {
        name: hexagrams[name]
        for name in {result.main_hexagram, result.mutual_hexagram, result.changed_hexagram}
    }
    allowed = [f"{a}-{b}" for a, b in candidate_scores(rule_prediction, 15)]
    rule_payload = rule_prediction.to_dict()
    # Unverified single-case hypotheses are visible as audit metadata only. Their
    # source score and exact effects are deliberately withheld from prematch AI.
    rule_payload["matched_rules"] = [
        {
            "id": rule.get("id", ""),
            "name": rule.get("name", ""),
            "status": rule.get("status", ""),
            "applied": bool(rule.get("applied", False)),
            "applied_scale": rule.get("applied_scale", 0.0),
            **(
                {
                    "conditions": rule.get("conditions", {}),
                    "effects": rule.get("effects", {}),
                    "lesson": rule.get("lesson", ""),
                }
                if rule.get("applied")
                else {}
            ),
        }
        for rule in rule_prediction.matched_rules
    ]

    case_payload = []
    for case in similar_cases:
        case_payload.append(
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
        )

    system_prompt = f"""
你是「梅花易數足球證據融合AI」，版本{PROMPT_VERSION}。你不是重新建立足球基線，也不是照抄規則；你的任務是審查有限卦象修正與歷史證據。

不可違反：
1. 只使用提供的賽前資料，只判90分鐘，不含延長賽與PK；不得使用或猜測本場賽後結果。
2. Python算出的字數、體卦、用卦、本卦、互卦、動爻、變卦不可更改。
3. 支持隊只決定體方，不代表體方強或必勝。
4. 「體生用、用剋體」只能是風險訊號，禁止單獨推出勝負。
5. 必須把本卦視為主局、互卦視為中段、動爻與變卦視為時段轉折；後段收束不等於前段不能進球。
6. Python已先用純足球先驗建立λ，再把卦象修正限制在單方±25%。你必須先審查足球基線，再審查卦象修正，最後處理兩者矛盾；不得要求卦象突破上限。
7. 足球實力分只能根據提供文字，不可憑模型記憶補充未提供事實。
8. 只能從allowed_score_candidates選3個比分，但候選池已包含體勝、平局、用勝，不能以規則原排序當成真理。
9. 證據不足時evidence_quality與direction_confidence必須降低；不得假裝高信心。
10. 歷史案例只提供可泛化教訓；單場產生且未通過留出驗證的假說不可當成固定規則，也不可直接複製舊比分。
11. 只輸出符合JSON Schema的物件。
""".strip()

    user_payload = {
        "current_match": {
            "match_name": match.match_name,
            "competition": match.competition,
            "scope": match.scope,
            "body_team": match.body_team,
            "use_team": match.use_team,
            "prematch_leaning": match.prematch_leaning,
            "body_prematch_text": _truncate(match.body_text, 1800),
            "use_prematch_text": _truncate(match.use_text, 1800),
            "full_neutral_prematch_text": _truncate(match.full_text, 3600),
            "context_notes": _truncate(match.context_notes, 1400),
            "manual_football_prior": {
                "body_strength_rating": match.body_strength_rating,
                "use_strength_rating": match.use_strength_rating,
                "prior_confidence": match.prior_confidence,
                "venue": match.venue,
            },
        },
        "immutable_hexagram_result": result.to_dict(),
        "rule_engine_prediction": rule_payload,
        "allowed_score_candidates": allowed,
        "confirmed_similar_case_count": len(similar_cases),
        "involved_trigram_knowledge": involved_trigrams,
        "involved_hexagram_knowledge": involved_hexagrams,
        "retrieved_historical_cases": case_payload,
        "decision_protocol": [
            "先確認football_prior中的足球基線λ與資料品質",
            "列出本互動變各自支持的節奏與方向",
            "確認卦象倍率沒有突破單方±25%上限",
            "檢查規則是否把體生用或轉艮過度放大",
            "若足球證據與卦象矛盾，明確寫入contradiction_warning",
            "從平衡候選池排序三個比分",
        ],
    }
    return system_prompt, json.dumps(user_payload, ensure_ascii=False, separators=(",", ":"))


def run_ai_prediction(
    client: GitHubModelsClient,
    match: MatchInput,
    result: HexagramResult,
    rule_prediction: RulePrediction,
    similar_cases: list[SimilarCase],
) -> AIAnalysis:
    system_prompt, user_prompt = build_prediction_prompt(match, result, rule_prediction, similar_cases)
    try:
        data, raw = client.infer_json(system_prompt, user_prompt)
        return _validate_ai_analysis(data, rule_prediction, "github_models", client.model, raw)
    except Exception as exc:
        return AIAnalysis(
            ok=False,
            provider="github_models",
            model=client.model,
            direction=rule_prediction.direction,
            scores=list(rule_prediction.scores),
            confidences=[0.0, 0.0, 0.0],
            score_reasons=["AI不可用，沿用v4足球先驗×有界卦象規則引擎。"] * 3,
            overall_reasoning="",
            risk_warning="",
            error=str(exc),
        )
