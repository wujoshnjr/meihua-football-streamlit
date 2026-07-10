from __future__ import annotations

import base64
import hashlib
import io
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import requests

from config import AppConfig
from evaluation import evaluate_predictions, final_scores, normalize_score
from models import AIAnalysis, HexagramResult, MatchInput, RulePrediction, SimilarCase


CASE_COLUMNS = [
    "案例ID", "建立時間", "更新時間", "比賽", "賽事", "判斷範圍", "體方", "用方", "賽前偏向",
    "體方段字數", "用方段字數", "全段總字數", "體卦", "體卦數", "體卦五行", "用卦", "用卦數", "用卦五行",
    "本卦", "互卦", "動爻", "動爻位置", "動爻層級", "變卦", "體方轉卦", "用方轉卦", "體用代碼", "體用生剋",
    "結構標籤", "規則版本", "規則首選比分", "規則第二選比分", "規則第三選比分", "規則方向", "規則信心",
    "AI啟用", "AI供應商", "AI模型", "Prompt版本", "AI首選比分", "AI第二選比分", "AI第三選比分", "AI方向", "AI信心",
    "AI推理摘要", "AI風險提醒", "AI相似案例", "AI建議規則", "最終首選比分", "最終第二選比分", "最終第三選比分",
    "實際比分", "首選命中", "第二選命中", "第三選命中", "三選一命中", "首選勝平負", "實際勝平負", "首選勝平負命中",
    "首選總進球誤差", "體方進球誤差", "用方進球誤差", "自動預測理由", "校準原因", "校準摘要", "人工確認AI校準",
    "相似案例IDs", "報告檔案", "體方賽前段落", "用方賽前段落", "完整賽前中性段落", "賽前補充資料"
]


class GitHubContentBackend:
    def __init__(self, config: AppConfig):
        self.config = config

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.config.github_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def _url(self, path: str) -> str:
        return f"https://api.github.com/repos/{self.config.github_repo}/contents/{path.strip('/')}"

    def get_text(self, path: str) -> tuple[str | None, str | None]:
        if not self.config.use_github_backend:
            return None, None
        response = requests.get(
            self._url(path),
            headers=self._headers(),
            params={"ref": self.config.github_branch},
            timeout=self.config.request_timeout_seconds,
        )
        if response.status_code == 404:
            return None, None
        response.raise_for_status()
        payload = response.json()
        content = base64.b64decode(payload["content"]).decode("utf-8-sig")
        return content, payload.get("sha")

    def put_text(self, path: str, text: str, message: str, retries: int = 1) -> dict[str, Any]:
        if not self.config.use_github_backend:
            return {}
        last_response: requests.Response | None = None
        for attempt in range(retries + 1):
            _, sha = self.get_text(path)
            body: dict[str, Any] = {
                "message": message,
                "content": base64.b64encode(text.encode("utf-8-sig")).decode("ascii"),
                "branch": self.config.github_branch,
            }
            if sha:
                body["sha"] = sha
            response = requests.put(
                self._url(path),
                headers=self._headers(),
                json=body,
                timeout=self.config.request_timeout_seconds,
            )
            last_response = response
            if response.status_code != 409:
                response.raise_for_status()
                return response.json()
            if attempt < retries:
                time.sleep(0.5)
        assert last_response is not None
        last_response.raise_for_status()
        return {}


class CaseStore:
    def __init__(self, config: AppConfig):
        self.config = config
        self.backend = GitHubContentBackend(config)
        self.local_csv = config.data_dir / "meihua_cases.csv"

    def load(self) -> pd.DataFrame:
        text: str | None = None
        if self.config.use_github_backend:
            text, _ = self.backend.get_text(self.config.github_cases_path)
        if text:
            df = pd.read_csv(io.StringIO(text.lstrip("\ufeff")), dtype="object", keep_default_na=False)
        elif self.local_csv.exists():
            df = pd.read_csv(self.local_csv, dtype="object", keep_default_na=False)
        else:
            df = pd.DataFrame(columns=CASE_COLUMNS)
        return self._normalize(df)

    def _normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        if df is None or df.empty:
            return pd.DataFrame(columns=CASE_COLUMNS).astype("object")
        df = df.copy().astype("object")
        for column in CASE_COLUMNS:
            if column not in df.columns:
                df[column] = ""
        ordered = CASE_COLUMNS + [column for column in df.columns if column not in CASE_COLUMNS]
        return df[ordered].fillna("").astype("object")

    def save(self, df: pd.DataFrame) -> None:
        df = self._normalize(df)
        csv_body = df.to_csv(index=False, lineterminator="\n")
        self.local_csv.parent.mkdir(parents=True, exist_ok=True)
        self.local_csv.write_text(csv_body, encoding="utf-8-sig")
        if self.config.use_github_backend:
            self.backend.put_text(
                self.config.github_cases_path,
                csv_body,
                "Update Meihua AI casebook",
                retries=1,
            )

    def upsert(self, row: dict[str, Any], mode: str = "自動更新") -> tuple[pd.DataFrame, str]:
        df = self.load().astype("object")
        safe_row = {key: "" if value is None else value for key, value in row.items()}
        for column in safe_row:
            if column not in df.columns:
                df[column] = ""

        key_columns = ["比賽", "體方", "用方", "本卦", "互卦", "動爻", "動爻位置", "變卦"]
        for column in key_columns:
            if column not in df.columns:
                df[column] = ""
        mask = pd.Series(True, index=df.index)
        for column in key_columns:
            mask &= df[column].astype(str).str.strip().eq(str(safe_row.get(column, "")).strip())
        matches = list(df[mask].index)

        if mode == "強制新增" or not matches:
            df = pd.concat([df, pd.DataFrame([safe_row])], ignore_index=True).astype("object")
            action = "新增"
        else:
            index = matches[-1]
            original_id = str(df.at[index, "案例ID"]).strip() if "案例ID" in df.columns else ""
            original_created = str(df.at[index, "建立時間"]).strip() if "建立時間" in df.columns else ""
            if original_id:
                safe_row["案例ID"] = original_id
            if original_created:
                safe_row["建立時間"] = original_created
            for key, value in safe_row.items():
                df.loc[index, key] = value
            action = "更新"
        self.save(df)
        return self._normalize(df), action

    @staticmethod
    def excel_bytes(df: pd.DataFrame) -> bytes:
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="cases")
        return output.getvalue()


def safe_filename(value: str) -> str:
    cleaned = re.sub(r'[\\/:*?"<>|]', "_", str(value or "")).strip()
    return cleaned or "match"


def new_case_id(result: HexagramResult) -> str:
    raw = f"{result.match_name}|{result.body_team}|{result.use_team}|{result.main_hexagram}|{datetime.now().isoformat()}"
    return "CASE-" + hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12].upper()


def save_report(config: AppConfig, result: HexagramResult, report: str) -> str:
    filename = safe_filename(result.match_name) + ".md"
    local_path = config.reports_dir / filename
    local_path.write_text(report, encoding="utf-8")
    if config.use_github_backend:
        remote_path = f"{config.github_reports_dir.strip('/')}/{filename}"
        GitHubContentBackend(config).put_text(remote_path, report, f"Update report: {result.match_name}", retries=1)
        return remote_path
    return str(local_path)


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
    chosen_scores = final_scores(rule_prediction, ai_analysis)
    metrics = evaluate_predictions(chosen_scores, actual_score)
    rule_scores = [f"{a}-{b}" for a, b in rule_prediction.scores]
    ai_scores = [f"{a}-{b}" for a, b in (ai_analysis.scores if ai_analysis else [])]
    final_score_texts = [f"{a}-{b}" for a, b in chosen_scores]
    while len(rule_scores) < 3:
        rule_scores.append("")
    while len(ai_scores) < 3:
        ai_scores.append("")
    while len(final_score_texts) < 3:
        final_score_texts.append("")

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ai_confidence = ""
    if ai_analysis and ai_analysis.confidences:
        ai_confidence = ",".join(f"{x:.3f}" for x in ai_analysis.confidences)

    return {
        "案例ID": new_case_id(result),
        "建立時間": now,
        "更新時間": now,
        "比賽": result.match_name,
        "賽事": match.competition,
        "判斷範圍": match.scope,
        "體方": result.body_team,
        "用方": result.use_team,
        "賽前偏向": match.prematch_leaning,
        "體方段字數": result.body_count,
        "用方段字數": result.use_count,
        "全段總字數": result.total_count,
        "體卦": result.body_gua,
        "體卦數": result.body_number,
        "體卦五行": result.body_element,
        "用卦": result.use_gua,
        "用卦數": result.use_number,
        "用卦五行": result.use_element,
        "本卦": result.main_hexagram,
        "互卦": result.mutual_hexagram,
        "動爻": result.moving_line,
        "動爻位置": result.moving_side,
        "動爻層級": result.moving_layer,
        "變卦": result.changed_hexagram,
        "體方轉卦": result.body_transition,
        "用方轉卦": result.use_transition,
        "體用代碼": result.relation_code,
        "體用生剋": result.relation,
        "結構標籤": "，".join(result.structural_tags),
        "規則版本": rule_prediction.method,
        "規則首選比分": rule_scores[0],
        "規則第二選比分": rule_scores[1],
        "規則第三選比分": rule_scores[2],
        "規則方向": rule_prediction.direction,
        "規則信心": rule_prediction.confidence,
        "AI啟用": "是" if ai_analysis and ai_analysis.ok else "否",
        "AI供應商": ai_analysis.provider if ai_analysis else "",
        "AI模型": ai_analysis.model if ai_analysis else "",
        "Prompt版本": "meihua-football-ai-v3.1.0" if ai_analysis else "",
        "AI首選比分": ai_scores[0],
        "AI第二選比分": ai_scores[1],
        "AI第三選比分": ai_scores[2],
        "AI方向": ai_analysis.direction if ai_analysis else "",
        "AI信心": ai_confidence,
        "AI推理摘要": ai_analysis.overall_reasoning if ai_analysis else "",
        "AI風險提醒": ai_analysis.risk_warning if ai_analysis else "",
        "AI相似案例": " | ".join(
            f"{item.get('case_id', '')}:{item.get('usable_lesson', '')}"
            for item in (ai_analysis.similar_case_analysis if ai_analysis else [])
        ),
        "AI建議規則": " | ".join(ai_analysis.calibration_suggestions if ai_analysis else []),
        "最終首選比分": final_score_texts[0],
        "最終第二選比分": final_score_texts[1],
        "最終第三選比分": final_score_texts[2],
        "實際比分": metrics["actual_score"],
        "首選命中": metrics["first_hit"],
        "第二選命中": metrics["second_hit"],
        "第三選命中": metrics["third_hit"],
        "三選一命中": metrics["any_hit"],
        "首選勝平負": metrics["first_outcome"],
        "實際勝平負": metrics["actual_outcome"],
        "首選勝平負命中": metrics["outcome_hit"],
        "首選總進球誤差": metrics["first_total_goal_error"],
        "體方進球誤差": metrics["body_goal_error"],
        "用方進球誤差": metrics["use_goal_error"],
        "自動預測理由": "；".join(rule_prediction.reasons),
        "校準原因": calibration_reason,
        "校準摘要": calibration_summary,
        "人工確認AI校準": "是" if confirmed_ai_calibration else "否",
        "相似案例IDs": "，".join(case.case_id for case in similar_cases),
        "報告檔案": report_path,
        "體方賽前段落": match.body_text,
        "用方賽前段落": match.use_text,
        "完整賽前中性段落": match.full_text,
        "賽前補充資料": match.context_notes,
    }
