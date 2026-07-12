from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any, Mapping

import pandas as pd

from config import AppConfig
from evaluation import controlled_final_scores, evaluate_predictions, outcome_brier, outcome_log_loss, score_tuple
from models import AIAnalysis, HexagramResult, MatchInput, RulePrediction, SimilarCase
from storage import GitHubContentBackend, safe_filename
from storage_v32 import (
    CASE_COLUMNS as V32_COLUMNS,
    CaseStore as V32CaseStore,
    build_case_row as build_case_row_v32,
)
from version import APP_VERSION, PROMPT_VERSION, RESEARCH_PROTOCOL_VERSION, SCHEMA_VERSION


V4_COLUMNS = [
    "資料結構版本",
    "系統版本",
    "研究協議版本",
    "預測模式",
    "預測內容雜湊",
    "鎖定狀態",
    "版本序號",
    "取代案例ID",
    "體方賽前實力",
    "用方賽前實力",
    "先驗可信度",
    "場地設定",
    "足球基線體方λ",
    "足球基線用方λ",
    "足球基線首選比分",
    "足球基線第二選比分",
    "足球基線第三選比分",
    "足球基線體勝機率",
    "足球基線平局機率",
    "足球基線用勝機率",
    "卦象體方倍率",
    "卦象用方倍率",
    "卦象修正上限",
    "卦象調整後體方λ",
    "卦象調整後用方λ",
    "卦線劇本版本",
    "劇本環境",
    "劇本能量走勢",
    "劇本開局",
    "劇本中段",
    "劇本終局",
    "比賽動能分",
    "破門通道分",
    "終局收束分",
    "反轉波動分",
    "體方能量歸屬",
    "用方能量歸屬",
    "體方完成通道",
    "用方完成通道",
    "鏡像判定",
    "零球閘門",
    "高比分閘門",
    "雙方進球訊號",
    "大勝方",
    "單向破門方",
    "總球錨點",
    "卦數錨點",
    "劇本候選比分",
    "劇本觸發理由",
    "劇本混合權重",
    "劇本期望體方進球",
    "劇本期望用方進球",
    "五球以上機率",
    "規則體勝機率",
    "規則平局機率",
    "規則用勝機率",
    "規則狀態快照",
    "規則診斷",
    "AI體方實力分",
    "AI用方實力分",
    "AI證據品質",
    "AI方向信心",
    "AI足球證據",
    "AI卦象證據",
    "AI矛盾警告",
    "AI連續劇本摘要",
    "AI開局解讀",
    "AI中段解讀",
    "AI終局解讀",
    "AI破門通道解讀",
    "AI能量歸屬解讀",
    "AI總球推理",
    "AI比分分配推理",
    "AI控制說明",
    "引擎版本",
    "足球基線首選命中",
    "足球基線三選一命中",
    "足球基線勝平負命中",
    "足球基線首選比分距離",
    "足球基線勝平負Brier",
    "卦象調整勝平負Brier",
    "足球基線LogLoss",
    "卦象調整LogLoss",
    "卦象是否改善",
]
CASE_COLUMNS = V32_COLUMNS + [column for column in V4_COLUMNS if column not in V32_COLUMNS]


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _score_texts(scores: list[tuple[int, int]]) -> list[str]:
    output = [f"{body}-{use}" for body, use in scores[:3]]
    return output + [""] * (3 - len(output))


def _triplet(row: Mapping[str, Any], prefix: str) -> list[tuple[int, int]]:
    output: list[tuple[int, int]] = []
    for suffix in ["首選比分", "第二選比分", "第三選比分"]:
        parsed = score_tuple(str(row.get(f"{prefix}{suffix}", "")))
        if parsed is not None:
            output.append(parsed)
    return output


def prediction_fingerprint(
    match: MatchInput,
    result: HexagramResult,
    rule_prediction: RulePrediction,
    ai_analysis: AIAnalysis | None,
    similar_cases: list[SimilarCase],
) -> str:
    ai_payload: dict[str, Any] | None = None
    if ai_analysis is not None:
        ai_payload = ai_analysis.to_dict()
        ai_payload.pop("raw_response", None)
    final, control = controlled_final_scores(rule_prediction, ai_analysis, len(similar_cases))
    payload = {
        "system_version": APP_VERSION,
        "research_protocol": RESEARCH_PROTOCOL_VERSION,
        "match": match.to_dict(),
        "hexagram": result.to_dict(),
        "rule": rule_prediction.to_dict(),
        "ai": ai_payload,
        "similar_case_ids": [case.case_id for case in similar_cases],
        "final_scores": final,
        "control": control,
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class CaseStore(V32CaseStore):
    def _normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        normalized = super()._normalize(df)
        if normalized is None or normalized.empty:
            return pd.DataFrame(columns=CASE_COLUMNS).astype("object")
        normalized = normalized.copy().astype("object")
        for column in CASE_COLUMNS:
            if column not in normalized.columns:
                normalized[column] = ""

        for index in normalized.index:
            # Canonicalize old v1-v3 score columns without destroying their originals.
            legacy = [
                str(normalized.at[index, column]).strip() if column in normalized.columns else ""
                for column in ["首選比分", "第二選比分", "第三選比分"]
            ]
            for position, suffix in enumerate(["首選比分", "第二選比分", "第三選比分"]):
                rule_column = f"規則{suffix}"
                final_column = f"最終{suffix}"
                ai_column = f"AI{suffix}"
                if not str(normalized.at[index, rule_column]).strip() and legacy[position]:
                    normalized.at[index, rule_column] = legacy[position]
                if not str(normalized.at[index, final_column]).strip():
                    normalized.at[index, final_column] = (
                        str(normalized.at[index, ai_column]).strip()
                        or str(normalized.at[index, rule_column]).strip()
                        or legacy[position]
                    )

            if not str(normalized.at[index, "資料結構版本"]).strip():
                normalized.at[index, "資料結構版本"] = "legacy"
            if not str(normalized.at[index, "系統版本"]).strip():
                normalized.at[index, "系統版本"] = "legacy"
            if not str(normalized.at[index, "預測模式"]).strip():
                normalized.at[index, "預測模式"] = "legacy"
            if not str(normalized.at[index, "鎖定狀態"]).strip():
                has_prediction = bool(str(normalized.at[index, "最終首選比分"]).strip())
                normalized.at[index, "鎖定狀態"] = "已鎖定" if has_prediction else "舊資料待整理"
            if not str(normalized.at[index, "版本序號"]).strip():
                normalized.at[index, "版本序號"] = 1

        ordered = CASE_COLUMNS + [column for column in normalized.columns if column not in CASE_COLUMNS]
        return normalized[ordered].where(pd.notna(normalized[ordered]), "").astype("object")

    def upsert(self, row: dict[str, Any], mode: str = "自動更新") -> tuple[pd.DataFrame, str]:
        """Save an immutable prematch version.

        Identical fingerprints are idempotent. A changed prediction for the same
        fixture becomes a new linked version, so a post-match result can never be
        blanked or silently attached to a later prediction.
        """
        df = self.load().astype("object")
        safe_row = {key: "" if value is None else value for key, value in row.items()}
        for column in CASE_COLUMNS:
            if column not in df.columns:
                df[column] = ""
        for column in safe_row:
            if column not in df.columns:
                df[column] = ""

        key_columns = ["比賽", "體方", "用方"]
        mask = pd.Series(True, index=df.index)
        for column in key_columns:
            mask &= df[column].astype(str).str.strip().eq(str(safe_row.get(column, "")).strip())
        matches = list(df[mask].index)

        latest_index = matches[-1] if matches else None
        incoming_hash = str(safe_row.get("預測內容雜湊") or safe_row.get("預測指紋") or "").strip()
        same_hash = False
        if latest_index is not None:
            existing_hash = str(
                df.at[latest_index, "預測內容雜湊"] or df.at[latest_index, "預測指紋"] or ""
            ).strip()
            same_hash = bool(incoming_hash and existing_hash and incoming_hash == existing_hash)

        if latest_index is not None and mode != "強制新增" and same_hash:
            protected = {
                "案例ID", "建立時間", "賽前鎖定時間", "版本序號", "取代案例ID",
                "實際比分", "賽果輸入時間", "校準狀態", "案例品質", "校準原因", "校準摘要",
                "人工確認AI校準", "AI校準JSON", "首選命中", "第二選命中", "第三選命中",
                "三選一命中", "首選勝平負", "實際勝平負", "首選勝平負命中",
                "首選總進球誤差", "體方進球誤差", "用方進球誤差",
                "規則首選命中", "規則三選一命中", "規則勝平負命中", "規則首選比分距離",
                "AI首選命中", "AI三選一命中", "AI勝平負命中", "AI首選比分距離",
                "最終首選命中", "最終三選一命中", "最終勝平負命中", "最終首選比分距離",
                "AI是否改善", "足球基線首選命中", "足球基線三選一命中", "足球基線勝平負命中",
                "足球基線首選比分距離", "足球基線勝平負Brier", "卦象調整勝平負Brier",
                "足球基線LogLoss", "卦象調整LogLoss", "卦象是否改善",
            }
            for key, value in safe_row.items():
                if key not in protected:
                    df.loc[latest_index, key] = value
            df.loc[latest_index, "更新時間"] = _now()
            action = "確認既有鎖定版本"
        else:
            prior_ids = [str(df.at[index, "案例ID"]).strip() for index in matches]
            versions: list[int] = []
            for index in matches:
                try:
                    versions.append(int(float(str(df.at[index, "版本序號"]).strip() or "1")))
                except ValueError:
                    versions.append(1)
            safe_row["版本序號"] = max(versions, default=0) + 1
            safe_row["取代案例ID"] = prior_ids[-1] if prior_ids else ""
            safe_row["鎖定狀態"] = "已鎖定"
            safe_row["賽前鎖定時間"] = safe_row.get("賽前鎖定時間") or _now()
            incoming = pd.DataFrame([safe_row]).astype("object")
            if df.empty:
                df = incoming
            else:
                df = pd.concat([df, incoming], ignore_index=True).astype("object")
            action = "強制新增鎖定版本" if mode == "強制新增" else ("新增預測版本" if matches else "新增鎖定案例")

        self.save(df)
        return self._normalize(df), action

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
        updated, info = super().update_postmatch(
            case_id=case_id,
            actual_score=actual_score,
            calibration_reason=calibration_reason,
            calibration_summary=calibration_summary,
            calibration_status=calibration_status,
            case_quality=case_quality,
            ai_calibration=ai_calibration,
            confirmed_ai=confirmed_ai,
        )
        matches = list(updated[updated["案例ID"].astype(str).str.strip().eq(str(case_id).strip())].index)
        if not matches:
            return updated, info
        index = matches[-1]
        row = updated.loc[index].to_dict()
        baseline_scores = _triplet(row, "足球基線")
        adjusted_scores = _triplet(row, "規則") or _triplet(row, "最終")
        baseline_metrics = evaluate_predictions(baseline_scores, actual_score)
        adjusted_metrics = evaluate_predictions(adjusted_scores, actual_score)
        baseline_probabilities = {
            "體方勝": row.get("足球基線體勝機率", ""),
            "平局": row.get("足球基線平局機率", ""),
            "用方勝": row.get("足球基線用勝機率", ""),
        }
        adjusted_probabilities = {
            "體方勝": row.get("規則體勝機率", ""),
            "平局": row.get("規則平局機率", ""),
            "用方勝": row.get("規則用勝機率", ""),
        }
        baseline_brier = outcome_brier(baseline_probabilities, actual_score)
        adjusted_brier = outcome_brier(adjusted_probabilities, actual_score)
        baseline_log_loss = outcome_log_loss(baseline_probabilities, actual_score)
        adjusted_log_loss = outcome_log_loss(adjusted_probabilities, actual_score)
        improvement = "未比較"
        if baseline_brier is not None and adjusted_brier is not None:
            improvement = "改善" if adjusted_brier < baseline_brier else ("惡化" if adjusted_brier > baseline_brier else "持平")

        v4_updates = {
            "足球基線首選命中": baseline_metrics["first_hit"],
            "足球基線三選一命中": baseline_metrics["any_hit"],
            "足球基線勝平負命中": baseline_metrics["outcome_hit"],
            "足球基線首選比分距離": baseline_metrics["first_score_distance"],
            "足球基線勝平負Brier": "" if baseline_brier is None else round(baseline_brier, 6),
            "卦象調整勝平負Brier": "" if adjusted_brier is None else round(adjusted_brier, 6),
            "足球基線LogLoss": "" if baseline_log_loss is None else round(baseline_log_loss, 6),
            "卦象調整LogLoss": "" if adjusted_log_loss is None else round(adjusted_log_loss, 6),
            "卦象是否改善": improvement,
        }
        for key, value in v4_updates.items():
            updated.loc[index, key] = value
        self.save(updated)
        return self._normalize(updated), {**info, **v4_updates}


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
    final, control = controlled_final_scores(rule_prediction, ai_analysis, len(similar_cases))
    final_texts = _score_texts(final)
    baseline_texts = _score_texts(rule_prediction.football_only_scores)
    probabilities = rule_prediction.outcome_probabilities or {}
    baseline_probabilities = rule_prediction.football_only_outcome_probabilities or {}
    fingerprint = prediction_fingerprint(match, result, rule_prediction, ai_analysis, similar_cases)
    rule_snapshot = [
        {
            "id": rule.get("id", ""),
            "status": rule.get("status", ""),
            "applied_scale": rule.get("applied_scale", 0.0),
            "applied": bool(rule.get("applied", False)),
        }
        for rule in rule_prediction.matched_rules
    ]
    script = rule_prediction.hexagram_script or {}

    row.update(
        {
            "資料結構版本": SCHEMA_VERSION,
            "系統版本": APP_VERSION,
            "研究協議版本": RESEARCH_PROTOCOL_VERSION,
            "預測內容雜湊": fingerprint,
            "預測指紋": fingerprint[:20],
            "鎖定狀態": "已鎖定",
            "版本序號": 1,
            "取代案例ID": "",
            "體方賽前實力": round(float(match.body_strength_rating), 2),
            "用方賽前實力": round(float(match.use_strength_rating), 2),
            "先驗可信度": round(float(match.prior_confidence), 3),
            "場地設定": match.venue,
            "足球基線體方λ": rule_prediction.football_expected_body_goals,
            "足球基線用方λ": rule_prediction.football_expected_use_goals,
            "足球基線首選比分": baseline_texts[0],
            "足球基線第二選比分": baseline_texts[1],
            "足球基線第三選比分": baseline_texts[2],
            "足球基線體勝機率": baseline_probabilities.get("體方勝", ""),
            "足球基線平局機率": baseline_probabilities.get("平局", ""),
            "足球基線用勝機率": baseline_probabilities.get("用方勝", ""),
            "卦象體方倍率": rule_prediction.hexagram_body_multiplier,
            "卦象用方倍率": rule_prediction.hexagram_use_multiplier,
            "卦象修正上限": rule_prediction.hexagram_adjustment_cap,
            "卦象調整後體方λ": rule_prediction.expected_body_goals,
            "卦象調整後用方λ": rule_prediction.expected_use_goals,
            "卦線劇本版本": script.get("version", ""),
            "劇本環境": script.get("environment", ""),
            "劇本能量走勢": script.get("trajectory", ""),
            "劇本開局": script.get("opening_reading", ""),
            "劇本中段": script.get("middle_reading", ""),
            "劇本終局": script.get("ending_reading", ""),
            "比賽動能分": script.get("dynamics_score", ""),
            "破門通道分": script.get("scoring_channel_score", ""),
            "終局收束分": script.get("closure_score", ""),
            "反轉波動分": script.get("volatility_score", ""),
            "體方能量歸屬": script.get("body_ownership", ""),
            "用方能量歸屬": script.get("use_ownership", ""),
            "體方完成通道": script.get("body_finishing", ""),
            "用方完成通道": script.get("use_finishing", ""),
            "鏡像判定": script.get("mirror_mode", ""),
            "零球閘門": "是" if script.get("zero_goal_gate") else "否",
            "高比分閘門": "是" if script.get("high_score_gate") else "否",
            "雙方進球訊號": "是" if script.get("btts_signal") else "否",
            "大勝方": script.get("rout_side", ""),
            "單向破門方": script.get("one_sided_side", ""),
            "總球錨點": json.dumps(script.get("total_goal_targets", []), ensure_ascii=False),
            "卦數錨點": json.dumps(script.get("numeric_signals", []), ensure_ascii=False, separators=(",", ":")),
            "劇本候選比分": json.dumps(script.get("candidate_scores", []), ensure_ascii=False, separators=(",", ":")),
            "劇本觸發理由": " | ".join(str(item) for item in script.get("reasons", [])),
            "劇本混合權重": rule_prediction.scenario_weight,
            "劇本期望體方進球": rule_prediction.scenario_expected_body_goals,
            "劇本期望用方進球": rule_prediction.scenario_expected_use_goals,
            "五球以上機率": rule_prediction.football_prior.get("five_plus_probability", ""),
            "規則體勝機率": probabilities.get("體方勝", ""),
            "規則平局機率": probabilities.get("平局", ""),
            "規則用勝機率": probabilities.get("用方勝", ""),
            "規則狀態快照": json.dumps(rule_snapshot, ensure_ascii=False, separators=(",", ":")),
            "規則診斷": " | ".join(rule_prediction.diagnostics),
            "AI體方實力分": round(float(ai_analysis.body_strength_score), 2) if ai_analysis else "",
            "AI用方實力分": round(float(ai_analysis.use_strength_score), 2) if ai_analysis else "",
            "AI證據品質": round(float(ai_analysis.evidence_quality), 3) if ai_analysis else "",
            "AI方向信心": round(float(ai_analysis.direction_confidence), 3) if ai_analysis else "",
            "AI足球證據": " | ".join(ai_analysis.football_evidence) if ai_analysis else "",
            "AI卦象證據": " | ".join(ai_analysis.hexagram_evidence) if ai_analysis else "",
            "AI矛盾警告": ai_analysis.contradiction_warning if ai_analysis else "",
            "AI連續劇本摘要": ai_analysis.match_script_summary if ai_analysis else "",
            "AI開局解讀": ai_analysis.opening_phase if ai_analysis else "",
            "AI中段解讀": ai_analysis.middle_phase if ai_analysis else "",
            "AI終局解讀": ai_analysis.ending_phase if ai_analysis else "",
            "AI破門通道解讀": ai_analysis.scoring_channel_analysis if ai_analysis else "",
            "AI能量歸屬解讀": ai_analysis.energy_ownership_analysis if ai_analysis else "",
            "AI總球推理": ai_analysis.total_goals_reasoning if ai_analysis else "",
            "AI比分分配推理": ai_analysis.score_allocation_reasoning if ai_analysis else "",
            "AI控制說明": control.get("note", ""),
            "AI控制模式": control.get("mode", ""),
            "AI權重": control.get("ai_weight", 0.0),
            "方向保護啟動": "是" if control.get("direction_guard") else "否",
            "Prompt版本": PROMPT_VERSION if ai_analysis else "",
            "引擎版本": rule_prediction.method,
            "規則版本": rule_prediction.method,
            "預測模式": "football_prior_x_hexagram_ai" if ai_analysis and ai_analysis.ok else "football_prior_x_hexagram",
            "最終首選比分": final_texts[0],
            "最終第二選比分": final_texts[1],
            "最終第三選比分": final_texts[2],
        }
    )
    return row


def save_report(config: AppConfig, result: HexagramResult, report: str) -> str:
    """Store reports by content hash so a later prediction cannot overwrite a lock."""
    report_hash = hashlib.sha256(report.encode("utf-8")).hexdigest()[:12]
    filename = f"{safe_filename(result.match_name)}__{report_hash}.md"
    local_path = config.reports_dir / filename
    local_path.parent.mkdir(parents=True, exist_ok=True)
    local_path.write_text(report, encoding="utf-8")
    if config.use_github_backend:
        remote_path = f"{config.github_reports_dir.strip('/')}/{filename}"
        GitHubContentBackend(config).put_text(remote_path, report, f"Lock prematch report: {result.match_name}", retries=1)
        return remote_path
    return str(local_path)


__all__ = [
    "CASE_COLUMNS",
    "CaseStore",
    "build_case_row",
    "prediction_fingerprint",
    "safe_filename",
    "save_report",
]
