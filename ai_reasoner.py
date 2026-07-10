from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

import requests

from knowledge_loader import load_hexagrams, load_trigrams
from models import AIAnalysis, HexagramResult, MatchInput, RulePrediction, SimilarCase


GITHUB_MODELS_ENDPOINT = "https://models.github.ai/inference/chat/completions"
GITHUB_MODELS_CATALOG = "https://models.github.ai/catalog/models"
GITHUB_MODELS_API_VERSION = "2026-03-10"
PROMPT_VERSION = "meihua-football-ai-v3.1.0"


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
            # 少數模型不接受 response_format；退回普通文字並仍要求只輸出 JSON。
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
        message = ""
        try:
            payload = response.json()
            message = payload.get("message") or payload.get("error", {}).get("message") or str(payload)
        except Exception:
            message = response.text[:500]
        if response.status_code == 401:
            hint = "Token 無效或已過期。"
        elif response.status_code == 403:
            hint = "Token 可能缺少 Models: Read-only，或該模型不對此帳號開放。"
        elif response.status_code == 404:
            hint = "模型 ID 可能不存在，請從 GitHub Models catalog 選擇有效模型。"
        elif response.status_code == 429:
            hint = "免費額度或速率限制已達上限；系統應改用本地規則引擎。"
        elif response.status_code >= 500:
            hint = "GitHub Models 服務暫時異常。"
        else:
            hint = "請查看 Streamlit log。"
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
    start = cleaned.find("{")
    end = cleaned.rfind("}")
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


def _score_tuple(value: Any) -> tuple[int, int] | None:
    text = str(value or "").strip().replace("：", "-").replace(":", "-").replace("–", "-").replace("—", "-")
    match = re.search(r"(?<!\d)(\d{1,2})\s*-\s*(\d{1,2})(?!\d)", text)
    if not match:
        return None
    body, use = int(match.group(1)), int(match.group(2))
    if body > 7 or use > 7:
        return None
    return body, use


def _validate_ai_analysis(
    data: dict[str, Any],
    rule_prediction: RulePrediction,
    provider: str,
    model: str,
    raw_response: dict[str, Any],
) -> AIAnalysis:
    candidates = data.get("score_candidates", [])
    if not isinstance(candidates, list):
        candidates = []
    scores: list[tuple[int, int]] = []
    confidences: list[float] = []
    score_reasons: list[str] = []
    for item in candidates:
        if not isinstance(item, dict):
            continue
        score = _score_tuple(item.get("score"))
        if score is None or score in scores:
            continue
        try:
            confidence = float(item.get("confidence", 0.0))
        except (TypeError, ValueError):
            confidence = 0.0
        confidence = max(0.0, min(1.0, confidence))
        scores.append(score)
        confidences.append(confidence)
        score_reasons.append(str(item.get("reason", "")).strip())
        if len(scores) == 3:
            break

    for score in rule_prediction.scores:
        if len(scores) == 3:
            break
        if score not in scores:
            scores.append(score)
            confidences.append(0.0)
            score_reasons.append("AI輸出不足，沿用固定規則引擎候選。")

    direction = str(data.get("result_direction", "")).strip() or rule_prediction.direction
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
你是「梅花易數足球決策支援 AI」，版本 {PROMPT_VERSION}。你的任務是比較結構、歸納校準教訓，並提出90分鐘比分候選。

不可違反的規則：
1. 目前比賽只准使用賽前資料，只判斷90分鐘，不含延長賽與PK。
2. 字數、體卦、用卦、本卦、互卦、動爻、變卦與五行關係是 Python 已算出的不可變事實，不得自行改卦。
3. 支持隊只是體方設定，不代表一定獲勝。
4. 歷史案例的實際比分可用來理解舊教訓；不得猜測或搜尋目前比賽的賽後結果。
5. 不要求卦象完全相同。要比較：五行流向、動爻所在方、轉象、開放/收束、破局/受阻與進球被高估或低估的原因。
6. 相似案例只可提供校準方向，禁止直接複製舊比分。
7. 不要輸出冗長思維過程，只提供可驗證的推理摘要。
8. 只輸出一個 JSON 物件，不要 Markdown，不要程式碼圍欄。

JSON格式：
{{
  "result_direction": "體方勝|平局|用方勝|一球差拉鋸",
  "score_candidates": [
    {{"score":"2-1","confidence":0.36,"reason":"一至兩句理由"}},
    {{"score":"1-1","confidence":0.28,"reason":"一至兩句理由"}},
    {{"score":"2-2","confidence":0.18,"reason":"一至兩句理由"}}
  ],
  "overall_reasoning": "整體卦勢鏈摘要",
  "risk_warning": "最容易低估或高估的風險",
  "similar_case_analysis": [
    {{"case_id":"...","usable_lesson":"可引用教訓","important_difference":"不可硬套之處"}}
  ],
  "calibration_suggestions": ["本場賽後值得驗證的規則"],
  "used_case_ids": ["..." ]
}}
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
        "involved_trigram_knowledge": involved_trigrams,
        "involved_hexagram_knowledge": involved_hexagrams,
        "retrieved_historical_cases": case_payload,
        "instruction": "請先比較結構相同點與差異，再重新排序三個90分鐘比分。若歷史案例不足，必須降低信心並以固定規則引擎為主。",
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
    system_prompt = """
你是梅花易數足球系統的賽後校準助手。現在允許使用使用者提供的實際90分鐘比分，但不得改寫賽前預測。
請誠實區分：命中、方向命中但比分錯、完全偏差。找出可泛化的結構教訓與只屬本場的偶然因素。
不得把一場結果直接變成永久規則；只輸出待人工確認的建議。只輸出JSON物件。
JSON格式：
{
  "accuracy_summary":"命中狀態",
  "error_type":"體方進球高估/用方進球低估/勝負方向錯/其他",
  "hexagram_cause":"本互動變與體用造成偏差的摘要",
  "generalizable_lesson":"可泛化教訓",
  "non_generalizable_factors":"本場偶然因素",
  "suggested_structural_tags":["..."],
  "suggested_calibration_reason":"可直接存入案例庫的校準原因",
  "rule_candidate":"待人工確認的新規則"
}
""".strip()
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
    data, raw = client.infer_json(system_prompt, json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    data["_raw_usage"] = raw.get("usage", {}) if isinstance(raw, dict) else {}
    return data
