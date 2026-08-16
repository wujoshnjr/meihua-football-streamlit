from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from typing import Any, Literal


EvidenceCategory = Literal[
    "official_schedule", "official_lineup", "injury", "suspension",
    "team_form", "travel", "venue", "weather", "other",
]


@dataclass(frozen=True)
class EvidenceItem:
    title: str
    url: str
    published_at: datetime
    retrieved_at: datetime
    category: EvidenceCategory
    team: Literal["home", "away", "neutral"] = "neutral"
    material_update: bool = False
    reliability: Literal["高", "中", "低"] = "中"


@dataclass
class MatchInput:
    match_id: str
    home_team: str
    away_team: str
    competition: str
    event_at: datetime
    timezone_name: str
    venue: str
    city: str
    evidence: list[EvidenceItem] = field(default_factory=list)
    both_teams_refreshed_after_material_update: bool = False
    scope: str = "90 分鐘＋補時，不含延長賽與點球"
    protocol_version: str = "qimen-football-prematch-v1.1.0"

    @property
    def freeze_at(self) -> datetime:
        return self.event_at - timedelta(hours=6)

    def cutoff_for(self, forecast_horizon: str) -> datetime:
        """Return the latest admissible instant for a registered forecast horizon."""

        if forecast_horizon == "EARLY":
            return self.freeze_at
        if forecast_horizon == "LINEUP":
            return self.event_at - timedelta(minutes=30)
        raise ValueError("forecast_horizon 必須為 EARLY 或 LINEUP")

    def validate(self) -> list[str]:
        errors: list[str] = []
        if self.event_at.tzinfo is None:
            errors.append("event_at 必須含 IANA 時區偏移")
        if not self.home_team.strip() or not self.away_team.strip():
            errors.append("主客隊名稱不可空白")
        if self.home_team.strip() == self.away_team.strip():
            errors.append("主隊與客隊不可相同")
        if self.scope != "90 分鐘＋補時，不含延長賽與點球":
            errors.append("勝負口徑必須鎖定為 90 分鐘＋補時，不含延長賽與點球")

        late_material = False
        for item in self.evidence:
            if not item.title.strip():
                errors.append("來源標題不可空白")
            if not item.url.strip():
                errors.append(f"來源「{item.title}」URL 不可空白")
            if item.published_at.tzinfo is None or item.retrieved_at.tzinfo is None:
                errors.append(f"來源「{item.title}」時間缺少時區")
                continue
            if item.published_at > item.retrieved_at:
                errors.append(f"來源「{item.title}」發布時間不可晚於擷取時間")
            if item.published_at >= self.event_at:
                errors.append(f"來源「{item.title}」在開賽後發布，禁止使用")
            if item.retrieved_at >= self.event_at:
                errors.append(f"來源「{item.title}」在開賽後擷取，歷史盲測禁止使用")
            if item.published_at > self.freeze_at or item.retrieved_at > self.freeze_at:
                if not item.material_update or item.category not in {"official_lineup", "injury", "suspension"}:
                    errors.append(f"來源「{item.title}」發布／擷取晚於 freeze_at，且不是重大先發／傷停更新")
                else:
                    late_material = True
        if late_material and not self.both_teams_refreshed_after_material_update:
            errors.append("freeze_at 後有重大更新時，必須同步刷新兩隊資料")
        return errors

    def integrity_status(self) -> dict[str, str]:
        errors = self.validate()
        return {
            "prematch_only": "PASS" if not any("開賽後" in e for e in errors) else "FAIL",
            "source_chronology": "PASS" if not any("晚於擷取時間" in e for e in errors) else "FAIL",
            "freeze_policy": "PASS" if not any("freeze_at" in e for e in errors) else "FAIL",
            "symmetric_update": "PASS" if not any("同步刷新" in e for e in errors) else "FAIL",
            "scope_lock": "PASS" if not any("勝負口徑" in e for e in errors) else "FAIL",
            "overall": "PASS" if not errors else "FAIL",
        }

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["event_at"] = self.event_at.isoformat()
        data["freeze_at"] = self.freeze_at.isoformat()
        for row in data["evidence"]:
            row["published_at"] = row["published_at"].isoformat()
            row["retrieved_at"] = row["retrieved_at"].isoformat()
        data["integrity"] = self.integrity_status()
        return data
