from __future__ import annotations

from typing import Any

import pandas as pd

from evaluation import controlled_final_scores
from models import AIAnalysis, HexagramResult, MatchInput, RulePrediction, SimilarCase
from storage_v32 import (
    CASE_COLUMNS as V32_COLUMNS,
    CaseStore as V32CaseStore,
    build_case_row as build_case_row_v32,
    safe_filename,
    save_report,
)


V33_COLUMNS = [
    "體方賽前實力",
    "用方賽前實力",
    "先驗可信度",
    "場地設定",
    "規則體勝機率",
    "規則平局機率",
    "規則用勝機率",
    "規則診斷",
    "AI體方實力分",
    "AI用方實力分",
    "AI證據品質",
    "AI方向信心",
    "AI足球證據",
    "AI卦象證據",
    "AI矛盾警告",
    "AI控制說明",
    "引擎版本",
]
CASE_COLUMNS = V32_COLUMNS + [column for column in V33_COLUMNS if column not in V32_COLUMNS]


class CaseStore(V32CaseStore):
    def _normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        normalized = super()._normalize(df)
        if normalized is None or normalized.empty:
            return pd.DataFrame(columns=CASE_COLUMNS).astype("object")
        normalized = normalized.copy().astype("object")
        for column in CASE_COLUMNS:
            if column not in normalized.columns:
                normalized[column] = ""
        ordered = CASE_COLUMNS + [column for column in normalized.columns if column not in CASE_COLUMNS]
        return normalized[ordered].fillna("").astype("object")


def build_case_row(
    match: MatchInput,
    result: HexagramResult,
    rule_prediction: RulePrediction,
    ai_analysis: AIAnalysis | None,
    similar_cases: list[SimilarCase],
    actual_score: str,
    calibration_reason: str,
    calibration_summary: str,
    confirmed_ai_calibration: bool,
    report_path: str,
) -> dict[str, Any]:
    row = build_case_row_v32(
        match,
        result,
        rule_prediction,
        ai_analysis,
        similar_cases,
        actual_score,
        calibration_reason,
        calibration_summary,
        confirmed_ai_calibration,
        report_path,
    )
    _, control = controlled_final_scores(rule_prediction, ai_analysis, len(similar_cases))
    probabilities = rule_prediction.outcome_probabilities or {}
    row.update(
        {
            "體方賽前實力": round(float(match.body_strength_rating), 2),
            "用方賽前實力": round(float(match.use_strength_rating), 2),
            "先驗可信度": round(float(match.prior_confidence), 3),
            "場地設定": match.venue,
            "規則體勝機率": probabilities.get("體方勝", ""),
            "規則平局機率": probabilities.get("平局", ""),
            "規則用勝機率": probabilities.get("用方勝", ""),
            "規則診斷": " | ".join(rule_prediction.diagnostics),
            "AI體方實力分": round(float(ai_analysis.body_strength_score), 2) if ai_analysis else "",
            "AI用方實力分": round(float(ai_analysis.use_strength_score), 2) if ai_analysis else "",
            "AI證據品質": round(float(ai_analysis.evidence_quality), 3) if ai_analysis else "",
            "AI方向信心": round(float(ai_analysis.direction_confidence), 3) if ai_analysis else "",
            "AI足球證據": " | ".join(ai_analysis.football_evidence) if ai_analysis else "",
            "AI卦象證據": " | ".join(ai_analysis.hexagram_evidence) if ai_analysis else "",
            "AI矛盾警告": ai_analysis.contradiction_warning if ai_analysis else "",
            "AI控制說明": control.get("note", ""),
            "AI控制模式": control.get("mode", ""),
            "AI權重": control.get("ai_weight", 0.0),
            "方向保護啟動": "是" if control.get("direction_guard") else "否",
            "Prompt版本": "meihua-football-ai-v3.3.0" if ai_analysis else "",
            "引擎版本": rule_prediction.method,
        }
    )
    return row


__all__ = ["CaseStore", "build_case_row", "safe_filename", "save_report", "CASE_COLUMNS"]
