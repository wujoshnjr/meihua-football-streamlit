from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Mapping

import requests

from evaluation import candidate_scores, score_tuple
from knowledge_loader import load_hexagrams, load_trigrams
from models import AIAnalysis, HexagramResult, MatchInput, RulePrediction, SimilarCase


GITHUB_MODELS_ENDPOINT = "https://models.github.ai/inference/chat/completions"
GITHUB_MODELS_CATALOG = "https://models.github.ai/catalog/models"
GITHUB_MODELS_API_VERSION = "2026-03-10"
PROMPT_VERSION = "meihua-football-ai-v3.2.0"


class GitHubModelsError(RuntimeError):
    pass


@dataclass(slots=True)
class GitHubModelsClient:
    token: str
    model: str
    timeout: int = 45
    max_tokens: int = 1600
    temperature: float = 0.2

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
        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "stream": False,
            "response_format": {"type": "json_object"},
        }
        response = requests.post(GITHUB_MODELS_ENDPOINT, headers=self._headers(), json=body, timeout=self.timeout)
        if response.status_code == 422:
            body.pop("response_format", None)
            response = requests.post(GITHUB_MODELS_ENDPOINT, headers=self._headers(), json=body, timeout=self.timeout)
        self._raise_for_status(response)
        payload = response.json()
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
            401: "Token 無效或已過期。",
            403: "Token 可能缺少 Models: Read-only，或該模型不對此帳號開放。",
            404: "模型 ID 可能不存在，請從 GitHub Models catalog 選擇有效模型。",
            429: "免費額度或速率限制已達上限；系統會退回本地規則引擎。",
        }
        hint = hints.get(response.status_code, "GitHub Models 服務暫時異常。" if response.status_code >= 500 else "請查看Streamlit log。")
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
            raise GitHubModelsError(f"AI 回傳的 JSON 無法解析：{exc}") from exc
    raise GitHubModelsError("AI 沒有回傳有效 JSON 物件")


def _truncate(text: str, limit: int) -> str:
    text = (text or "").strip()
    return text if len(text) <= limit else text[:limit] + "…"


def _validate_ai_analysis(
    data: dict[str, Any],
    rule_prediction: RulePrediction,
    provider: str,
    model: str,
    raw_response: dict[str, Any],
) -> AIAnalysis:
    allowed = candidate_scores(rule_prediction, 12)
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
        try:
            confidence = float(item.get("confidence", 0.0))
        except (TypeError, ValueError):
            confidence = 0.0
        scores.append(score)
        confidences.append(max(0.0, min(1.0, confidence)))
        score_reasons.append(str(item.get("reason", "")).strip())
        if len(scores) == 3:
            break

    for score in rule_prediction.scores:
        if len(scores) == 3:
            break
        if score not in scores:
            scores.append(score)
            confidences.append(0.0)
            score_reasons.append("AI未提供有效候選，沿用固定規則順位。")

    similar_case_analysis = data.get("similar_case_analysis", [])
    if not isinstance(similar_case_analysis, list):
        similar_case_analysis = []
    suggestions = data.get("calibration_suggestions", [])
    if isinstance(suggestions, str):
        suggestions = [suggestions]
    used_ids = data.get("used_case_ids", [])
    if isinstance(used_ids, str):
        used_ids = [used_ids]

    return AIAnalysis(
        ok=True,
        provider=provider,
        model=model,
        direction=str(data.get("result_direction", "")).strip() or rule_prediction.direction,
        scores=scores[:3],
        confidences=confidences[:3],
        score_reasons=score_reasons[:3],
        overall_reasoning=str(data.get("overall_reasoning", "")).strip(),
        risk_warning=str(data.get("risk_warning", "")).strip(),
        similar_case_analysis=[x for x in similar_case_analysis if isinstance(x, dict)][:8],
        calibration_suggestions=[str(x).strip() for x in suggestions if str(x).strip()][:8] if isinstance(suggestions, list) else [],
        used_case_ids=[str(x).strip() for x in used_ids if str(x).strip()][:10] if isinstance(used_ids, list) else [],
        raw_response=raw_response,
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
    allowed = [f"{a}-{b}" for a, b in candidate_scores(rule_prediction, 12)]

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
你是「梅花易數足球決策支援AI」，版本 {PROMPT_VERSION}。只負責比較結構與有限重排，不得推翻固定起卦。
不可違反：
1. 只用賽前資料，只判90分鐘，不含延長賽與PK。
2. Python算出的字數、體用、本互動變與五行關係不可更改。
3. 支持隊只決定體方，不代表必勝。
4. 只能從 allowed_score_candidates 選3個比分，禁止創造池外比分。
5. 相似案例少於3場時，不得改變固定規則首選的勝平負方向。
6. 相似案例只提供校準方向，不可直接複製舊比分。
7. 只輸出JSON，不要Markdown。
JSON欄位：result_direction、score_candidates、overall_reasoning、risk_warning、similar_case_analysis、calibration_suggestions、used_case_ids。
""".strip()

    user_payload = {
        "current_match": {
            "match_name": match.match_name,
            "competition": match.competition,
            "scope": match.scope,
            "body_team": match.body_team,
            "use_team": match.use_team,
            "prematch_leaning": match.prematch_leaning,
            "body_prematch_text": _truncate(match.body_text, 1600),
            "use_prematch_text": _truncate(match.use_text, 1600),
            "full_neutral_prematch_text": _truncate(match.full_text, 3200),
            "context_notes": _truncate(match.context_notes, 1000),
        },
        "immutable_hexagram_result": result.to_dict(),
        "rule_engine_prediction": rule_prediction.to_dict(),
        "allowed_score_candidates": allowed,
        "confirmed_similar_case_count": len(similar_cases),
        "involved_trigram_knowledge": involved_trigrams,
        "involved_hexagram_knowledge": involved_hexagrams,
        "retrieved_historical_cases": case_payload,
        "instruction": "先比較共同點與差異，再只從候選池重排3個比分。案例不足時降低信心並保留規則方向。",
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
            score_reasons=["AI不可用，沿用固定規則引擎。"] * 3,
            overall_reasoning="",
            risk_warning="",
            error=str(exc),
        )


def run_postmatch_calibration(
    client: GitHubModelsClient,
    match: MatchInput,
    result: HexagramResult,
    rule_prediction: RulePrediction,
    ai_analysis: AIAnalysis | None,
    actual_score: str,
    user_review: str,
    similar_cases: list[SimilarCase],
) -> dict[str, Any]:
    payload = {
        "match": match.match_name,
        "scope": match.scope,
        "immutable_hexagram_result": result.to_dict(),
        "prematch_rule_prediction": rule_prediction.to_dict(),
        "prematch_ai_prediction": ai_analysis.to_dict() if ai_analysis else None,
        "actual_90_minute_score": actual_score,
        "user_review": user_review,
        "similar_historical_cases": [case.to_dict() for case in similar_cases[:5]],
    }
    return _run_postmatch_payload(client, payload)


def run_postmatch_calibration_from_row(
    client: GitHubModelsClient,
    row: Mapping[str, Any],
    actual_score: str,
    user_review: str,
) -> dict[str, Any]:
    safe_row = {str(k): str(v or "") for k, v in row.items()}
    payload = {
        "stored_prematch_case": safe_row,
        "actual_90_minute_score": actual_score,
        "user_review": user_review,
        "instruction": "只能校準已鎖定的賽前預測，不得改寫當時預測。將教訓分成精確案例層、結構層、通用層。",
    }
    return _run_postmatch_payload(client, payload)


def _run_postmatch_payload(client: GitHubModelsClient, payload: Mapping[str, Any]) -> dict[str, Any]:
    system_prompt = """
你是梅花易數足球系統的賽後校準助手。允許使用使用者輸入的實際90分鐘比分，但不得改寫賽前預測。
請誠實區分精確命中、方向命中、完全偏差；輸出可泛化結構教訓，且不得把單一結果直接變成永久規則。
只輸出JSON：accuracy_summary、error_type、hexagram_cause、generalizable_lesson、non_generalizable_factors、suggested_structural_tags、suggested_calibration_reason、rule_candidate。
""".strip()
    data, raw = client.infer_json(system_prompt, json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    data["_raw_usage"] = raw.get("usage", {}) if isinstance(raw, dict) else {}
    return data
