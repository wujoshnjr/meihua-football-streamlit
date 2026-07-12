from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any, Mapping

import pandas as pd

from evaluation import controlled_final_scores, evaluate_predictions, normalize_score, score_tuple
from models import AIAnalysis, HexagramResult, MatchInput, RulePrediction, SimilarCase
from storage import (
    CASE_COLUMNS as V31_COLUMNS,
    CaseStore as BaseCaseStore,
    build_case_row as build_case_row_v31,
    safe_filename,
    save_report,
)


V32_COLUMNS = [
    "預測指紋", "賽前鎖定時間", "賽果輸入時間", "校準狀態", "案例品質", "AI校準JSON",
    "AI控制模式", "AI權重", "相似已確認案例數", "方向保護啟動",
    "規則首選命中", "規則三選一命中", "規則勝平負命中", "規則首選比分距離",
    "AI首選命中", "AI三選一命中", "AI勝平負命中", "AI首選比分距離",
    "最終首選命中", "最終三選一命中", "最終勝平負命中", "最終首選比分距離", "AI是否改善",
]
CASE_COLUMNS = V31_COLUMNS + [column for column in V32_COLUMNS if column not in V31_COLUMNS]


def _stable_legacy_id(row: pd.Series) -> str:
    raw = "|".join(
        str(row.get(column, "")).strip()
        for column in ["比賽", "體方", "用方", "建立時間", "本卦", "變卦"]
    )
    return "LEGACY-" + hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12].upper()


def _triplet(row: Mapping[str, Any], prefix: str, legacy: bool = False) -> list[tuple[int, int]]:
    names = [f"{prefix}首選比分", f"{prefix}第二選比分", f"{prefix}第三選比分"]
    if legacy:
        names = ["首選比分", "第二選比分", "第三選比分"]
    output: list[tuple[int, int]] = []
    for name in names:
        parsed = score_tuple(str(row.get(name, "")))
        if parsed is not None:
            output.append(parsed)
    return output


class CaseStore(BaseCaseStore):
    def _normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        if df is None or df.empty:
            return pd.DataFrame(columns=CASE_COLUMNS).astype("object")
        df = df.copy().astype("object")
        for column in CASE_COLUMNS:
            if column not in df.columns:
                df[column] = ""
        for index in df.index:
            if not str(df.at[index, "案例ID"]).strip():
                df.at[index, "案例ID"] = _stable_legacy_id(df.loc[index])
            if not str(df.at[index, "校準狀態"]).strip():
                actual = str(df.at[index, "實際比分"]).strip()
                reason = str(df.at[index, "校準原因"]).strip()
                df.at[index, "校準狀態"] = "已確認" if actual and reason else ("待確認" if actual else "未輸入")
            if not str(df.at[index, "案例品質"]).strip():
                df.at[index, "案例品質"] = "中"
        ordered = CASE_COLUMNS + [column for column in df.columns if column not in CASE_COLUMNS]
        ordered_df = df[ordered]
        return ordered_df.where(pd.notna(ordered_df), "").astype("object")

    def get_by_id(self, case_id: str) -> dict[str, Any] | None:
        df = self.load()
        matches = df[df["案例ID"].astype(str).str.strip().eq(str(case_id).strip())]
        if matches.empty:
            return None
        return {str(k): v for k, v in matches.iloc[-1].to_dict().items()}

    def update_postmatch(
        self,
        case_id: str,
        actual_score: str,
        calibration_reason: str,
        calibration_summary: str,
        calibration_status: str = "待確認",
        case_quality: str = "中",
        ai_calibration: Mapping[str, Any] | None = None,
        confirmed_ai: bool = False,
    ) -> tuple[pd.DataFrame, dict[str, Any]]:
        actual = normalize_score(actual_score)
        if not actual:
            raise ValueError("請輸入有效的90分鐘比分，例如 2-1。")
        df = self.load().astype("object")
        matches = list(df[df["案例ID"].astype(str).str.strip().eq(str(case_id).strip())].index)
        if not matches:
            raise KeyError(f"找不到案例ID：{case_id}")
        index = matches[-1]
        row = df.loc[index].to_dict()
        rule_scores = _triplet(row, "規則") or _triplet(row, "", legacy=True)
        ai_scores = _triplet(row, "AI")
        final_scores = _triplet(row, "最終") or ai_scores or rule_scores
        rule_metrics = evaluate_predictions(rule_scores, actual)
        ai_metrics = evaluate_predictions(ai_scores, actual)
        final_metrics = evaluate_predictions(final_scores, actual)
        ai_improvement = "未比較"
        if ai_scores and rule_scores:
            ai_distance = ai_metrics.get("first_score_distance")
            rule_distance = rule_metrics.get("first_score_distance")
            if isinstance(ai_distance, int) and isinstance(rule_distance, int):
                ai_improvement = "改善" if ai_distance < rule_distance else ("惡化" if ai_distance > rule_distance else "持平")

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        updates: dict[str, Any] = {
            "更新時間": now,
            "賽果輸入時間": now,
            "實際比分": actual,
            "校準原因": calibration_reason.strip(),
            "校準摘要": calibration_summary.strip(),
            "校準狀態": calibration_status,
            "案例品質": case_quality,
            "人工確認AI校準": "是" if confirmed_ai else "否",
            "AI校準JSON": json.dumps(dict(ai_calibration or {}), ensure_ascii=False, separators=(",", ":")) if ai_calibration else "",
            "首選命中": final_metrics["first_hit"],
            "第二選命中": final_metrics["second_hit"],
            "第三選命中": final_metrics["third_hit"],
            "三選一命中": final_metrics["any_hit"],
            "首選勝平負": final_metrics["first_outcome"],
            "實際勝平負": final_metrics["actual_outcome"],
            "首選勝平負命中": final_metrics["outcome_hit"],
            "首選總進球誤差": final_metrics["first_total_goal_error"],
            "體方進球誤差": final_metrics["body_goal_error"],
            "用方進球誤差": final_metrics["use_goal_error"],
            "規則首選命中": rule_metrics["first_hit"],
            "規則三選一命中": rule_metrics["any_hit"],
            "規則勝平負命中": rule_metrics["outcome_hit"],
            "規則首選比分距離": rule_metrics["first_score_distance"],
            "AI首選命中": ai_metrics["first_hit"],
            "AI三選一命中": ai_metrics["any_hit"],
            "AI勝平負命中": ai_metrics["outcome_hit"],
            "AI首選比分距離": ai_metrics["first_score_distance"],
            "最終首選命中": final_metrics["first_hit"],
            "最終三選一命中": final_metrics["any_hit"],
            "最終勝平負命中": final_metrics["outcome_hit"],
            "最終首選比分距離": final_metrics["first_score_distance"],
            "AI是否改善": ai_improvement,
        }
        for key, value in updates.items():
            if key not in df.columns:
                df[key] = ""
            df.loc[index, key] = value
        self.save(df)
        return self._normalize(df), {"case_id": case_id, **updates}


def _fingerprint(match: MatchInput, result: HexagramResult, rule_prediction: RulePrediction) -> str:
    raw = json.dumps(
        {"match": match.to_dict(), "hexagram": result.to_dict(), "rule": rule_prediction.to_dict()},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]


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
    row = build_case_row_v31(
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
    final, control = controlled_final_scores(rule_prediction, ai_analysis, len(similar_cases))
    final_texts = [f"{a}-{b}" for a, b in final]
    while len(final_texts) < 3:
        final_texts.append("")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    row.update(
        {
            "預測指紋": _fingerprint(match, result, rule_prediction),
            "賽前鎖定時間": row.get("建立時間") or now,
            "賽果輸入時間": now if normalize_score(actual_score) else "",
            "校準狀態": "已確認" if normalize_score(actual_score) and calibration_reason.strip() else "未輸入",
            "案例品質": "中",
            "AI校準JSON": "",
            "最終首選比分": final_texts[0],
            "最終第二選比分": final_texts[1],
            "最終第三選比分": final_texts[2],
            "AI控制模式": control.get("mode", ""),
            "AI權重": control.get("ai_weight", 0.0),
            "相似已確認案例數": len(similar_cases),
            "方向保護啟動": "是" if control.get("direction_guard") else "否",
            "Prompt版本": "meihua-football-ai-v3.2.0" if ai_analysis else "",
        }
    )
    return row
