from __future__ import annotations

import base64
import csv
import hashlib
import io
import json
import re
import time
from typing import Any, Mapping, Sequence

import requests

from config import AppConfig
from casting_structure import build_casting_structure
from export_builder import build_stored_casting_payload
from models import CastingInput, HexagramResult
from version import APP_VERSION, SCHEMA_VERSION


CASTING_COLUMNS = [
    "資料結構版本", "系統版本", "排卦ID", "建立時間", "起卦國曆ISO", "起卦農曆時間",
    "起卦時區", "農曆年份", "農曆年干支", "農曆月份", "是否閏月", "農曆日",
    "起卦時辰", "起卦干支時辰", "日辰", "日干", "日支", "月令", "旬名", "旬空",
    "標題", "類別", "範圍", "體方名稱", "用方名稱",
    "體方段字數", "體方除八餘數", "體卦", "體卦數", "體卦五行",
    "用方段字數", "用方除八餘數", "用卦", "用卦數", "用卦五行",
    "完整段落字數", "完整段落除六餘數", "本卦", "本卦六爻自下而上",
    "互卦下卦", "互卦上卦", "互卦", "互卦六爻自下而上",
    "動爻", "動爻爻名", "動爻原陰陽", "動爻變後陰陽", "動爻所屬", "動爻層級",
    "本卦宮", "本卦宮位", "本卦世爻", "本卦應爻", "動爻納甲", "動爻六親（日干）", "動爻六親（卦宮）", "動爻旬空",
    "變卦", "變卦六爻自下而上", "變後體卦", "變後用卦", "體卦轉象", "用卦轉象",
    "本卦體用關係代碼", "本卦體用關係", "變卦體用關係代碼", "變卦體用關係",
    "排卦計算版本", "排卦指紋", "完整排盤JSON", "報告檔案",
    "體方原文", "用方原文", "完整中性原文", "補充資料",
]


def safe_filename(value: str) -> str:
    cleaned = re.sub(r'[\\/:*?"<>|]', "_", str(value or "")).strip()
    return cleaned or "casting"


def casting_fingerprint(casting: CastingInput, result: HexagramResult) -> str:
    payload = {"input": casting.to_dict(), "result": result.to_dict(), "system_version": APP_VERSION}
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def new_casting_id(fingerprint: str) -> str:
    return "CAST-" + fingerprint[:12].upper()


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
        return base64.b64decode(payload["content"]).decode("utf-8-sig"), payload.get("sha")

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


class CastingStore:
    def __init__(self, config: AppConfig):
        self.config = config
        self.backend = GitHubContentBackend(config)
        self.local_csv = config.data_dir / "meihua_castings.csv"

    @staticmethod
    def _normalize(rows: Sequence[Mapping[str, Any]] | None) -> list[dict[str, str]]:
        if not rows:
            return []
        extras: list[str] = []
        for row in rows:
            for column in row:
                if column not in CASTING_COLUMNS and column not in extras:
                    extras.append(column)
        columns = CASTING_COLUMNS + extras
        return [
            {
                column: "" if row.get(column) is None else str(row.get(column, ""))
                for column in columns
            }
            for row in rows
        ]

    @classmethod
    def _read_csv(cls, text: str) -> list[dict[str, str]]:
        reader = csv.DictReader(io.StringIO(text.lstrip("\ufeff")))
        return cls._normalize(list(reader))

    @classmethod
    def _csv_text(cls, rows: Sequence[Mapping[str, Any]]) -> str:
        normalized = cls._normalize(rows)
        extras = [
            column
            for row in normalized
            for column in row
            if column not in CASTING_COLUMNS
        ]
        columns = CASTING_COLUMNS + list(dict.fromkeys(extras))
        output = io.StringIO(newline="")
        writer = csv.DictWriter(output, fieldnames=columns, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(normalized)
        return output.getvalue()

    def load(self) -> list[dict[str, str]]:
        text: str | None = None
        if self.config.use_github_backend:
            text, _ = self.backend.get_text(self.config.github_castings_path)
        if text:
            return self._read_csv(text)
        if self.local_csv.exists():
            return self._read_csv(self.local_csv.read_text(encoding="utf-8-sig"))
        return []

    def save(self, rows: Sequence[Mapping[str, Any]]) -> None:
        csv_body = self._csv_text(rows)
        self.local_csv.parent.mkdir(parents=True, exist_ok=True)
        self.local_csv.write_text(csv_body, encoding="utf-8-sig")
        if self.config.use_github_backend:
            self.backend.put_text(
                self.config.github_castings_path,
                csv_body,
                "Update Meihua casting records",
                retries=1,
            )

    def upsert(self, row: Mapping[str, Any]) -> tuple[list[dict[str, str]], str]:
        rows = self.load()
        fingerprint = str(row.get("排卦指紋", "")).strip()
        matches = [
            index
            for index, existing in enumerate(rows)
            if fingerprint and str(existing.get("排卦指紋", "")).strip() == fingerprint
        ]
        safe_row = {key: "" if value is None else str(value) for key, value in row.items()}
        if matches:
            index = matches[-1]
            safe_row["排卦ID"] = rows[index].get("排卦ID", safe_row.get("排卦ID", ""))
            safe_row["建立時間"] = rows[index].get("建立時間", safe_row.get("建立時間", ""))
            rows[index].update(safe_row)
            action = "確認既有排卦"
        else:
            rows.append(safe_row)
            action = "新增排卦"
        normalized = self._normalize(rows)
        self.save(normalized)
        return normalized, action

    @classmethod
    def csv_bytes(cls, rows: Sequence[Mapping[str, Any]]) -> bytes:
        return ("\ufeff" + cls._csv_text(rows)).encode("utf-8")

    @classmethod
    def public_csv_bytes(cls, rows: Sequence[Mapping[str, Any]]) -> bytes:
        """Return a readable record table without raw audit JSON or fingerprint code."""

        hidden = {"完整排盤JSON", "排卦指紋"}
        public_rows = [{key: value for key, value in row.items() if key not in hidden} for row in rows]
        normalized = cls._normalize(public_rows)
        columns = [column for column in normalized[0] if column not in hidden] if normalized else []
        output = io.StringIO(newline="")
        writer = csv.DictWriter(output, fieldnames=columns, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(normalized)
        return ("\ufeff" + output.getvalue()).encode("utf-8")


def build_casting_row(
    casting: CastingInput,
    result: HexagramResult,
    report_path: str = "",
) -> dict[str, Any]:
    fingerprint = casting_fingerprint(casting, result)
    structure = build_casting_structure(result)
    najia = structure["najia_analysis"]
    day = najia["day_cycle"]
    void = najia["xun_void"]
    main_chart = najia["main_hexagram"]
    moving_line = main_chart["lines"][result.moving_line - 1]
    return {
        "資料結構版本": SCHEMA_VERSION,
        "系統版本": APP_VERSION,
        "排卦ID": new_casting_id(fingerprint),
        "建立時間": result.casting_moment.gregorian_text,
        "起卦國曆ISO": result.casting_moment.gregorian_iso,
        "起卦農曆時間": result.casting_moment.lunar_text,
        "起卦時區": f"{result.casting_moment.timezone}／{result.casting_moment.utc_offset}",
        "農曆年份": result.casting_moment.lunar_year,
        "農曆年干支": result.casting_moment.lunar_year_ganzhi,
        "農曆月份": f"{result.casting_moment.lunar_month_text}月",
        "是否閏月": "是" if result.casting_moment.lunar_is_leap_month else "否",
        "農曆日": result.casting_moment.lunar_day_text,
        "起卦時辰": f"{result.casting_moment.shichen}時",
        "起卦干支時辰": f"{result.casting_moment.shichen_ganzhi}時",
        "日辰": f"{day['day_ganzhi']}日",
        "日干": f"{day['day_stem']}（{day['day_stem_element']}）",
        "日支": day["day_branch"],
        "月令": f"{day['month_branch']}月（{day['month_element']}）",
        "旬名": void["xun_name"],
        "旬空": void["void_text"],
        "標題": result.title,
        "類別": casting.category,
        "範圍": casting.scope,
        "體方名稱": result.body_name,
        "用方名稱": result.use_name,
        "體方段字數": result.body_count,
        "體方除八餘數": result.body_modulo,
        "體卦": result.body_gua,
        "體卦數": result.body_number,
        "體卦五行": result.body_element,
        "用方段字數": result.use_count,
        "用方除八餘數": result.use_modulo,
        "用卦": result.use_gua,
        "用卦數": result.use_number,
        "用卦五行": result.use_element,
        "完整段落字數": result.total_count,
        "完整段落除六餘數": result.moving_modulo,
        "本卦": result.main_hexagram,
        "本卦六爻自下而上": result.main_lines_bottom_up,
        "互卦下卦": result.mutual_lower_gua,
        "互卦上卦": result.mutual_upper_gua,
        "互卦": result.mutual_hexagram,
        "互卦六爻自下而上": result.mutual_lines_bottom_up,
        "動爻": result.moving_line,
        "動爻爻名": result.moving_line_label,
        "動爻原陰陽": result.moving_original_type,
        "動爻變後陰陽": result.moving_changed_type,
        "動爻所屬": result.moving_side,
        "動爻層級": result.moving_layer,
        "本卦宮": f"{main_chart['palace']}宮（{main_chart['palace_element']}）",
        "本卦宮位": main_chart["palace_stage"],
        "本卦世爻": f"第{main_chart['world_line']}爻 {main_chart['world_line_label']}",
        "本卦應爻": f"第{main_chart['response_line']}爻 {main_chart['response_line_label']}",
        "動爻納甲": moving_line["gan_zhi"],
        "動爻六親（日干）": moving_line["six_relative_by_day_stem"],
        "動爻六親（卦宮）": moving_line["six_relative_by_palace"],
        "動爻旬空": moving_line["void_status"],
        "變卦": result.changed_hexagram,
        "變卦六爻自下而上": result.changed_lines_bottom_up,
        "變後體卦": result.changed_body_gua,
        "變後用卦": result.changed_use_gua,
        "體卦轉象": result.body_transition,
        "用卦轉象": result.use_transition,
        "本卦體用關係代碼": result.relation_code,
        "本卦體用關係": result.relation,
        "變卦體用關係代碼": result.changed_relation_code,
        "變卦體用關係": result.changed_relation,
        "排卦計算版本": result.calculation_version,
        "排卦指紋": fingerprint,
        "完整排盤JSON": json.dumps(
            build_stored_casting_payload(result),
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        "報告檔案": report_path,
        "體方原文": casting.body_text,
        "用方原文": casting.use_text,
        "完整中性原文": casting.full_text,
        "補充資料": casting.context_notes,
    }


def save_report(config: AppConfig, row: Mapping[str, Any], report: str) -> str:
    filename = f"{safe_filename(str(row.get('標題', 'casting')))}_{row.get('排卦ID', '')}.html"
    local_path = config.reports_dir / filename
    local_path.write_text(report, encoding="utf-8")
    if config.use_github_backend:
        remote_path = f"{config.github_reports_dir.strip('/')}/{filename}"
        GitHubContentBackend(config).put_text(remote_path, report, f"Save casting: {row.get('標題', '')}", retries=1)
        return remote_path
    return str(local_path)


__all__ = [
    "CASTING_COLUMNS",
    "CastingStore",
    "GitHubContentBackend",
    "build_casting_row",
    "casting_fingerprint",
    "new_casting_id",
    "safe_filename",
    "save_report",
]
