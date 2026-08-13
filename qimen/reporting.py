from __future__ import annotations

import hashlib
import json
from datetime import datetime
from html import escape
from typing import Any

from .football import FootballReading
from .models import QimenBoard
from .protocol import MatchInput


def canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def build_bundle(
    match: MatchInput,
    board: QimenBoard,
    reading: FootballReading,
    *,
    locked_at: datetime | None = None,
) -> dict[str, Any]:
    """Return one audit-friendly export with data, method and integrity status."""

    core = {
        "schema_version": "qimen-football-bundle-v1.0.0",
        "match": match.to_dict(),
        "board": board.to_dict(),
        "football_reading": reading.to_dict(),
        "locked_at": locked_at.isoformat() if locked_at else None,
        "boundaries": {
            "knowledge_application_separation": True,
            "automatic_winner": False,
            "automatic_fixed_score": False,
            "probability_claim": False,
            "scope": match.scope,
        },
    }
    core["fingerprint_sha256"] = hashlib.sha256(
        canonical_json(core).encode("utf-8")
    ).hexdigest()
    return core


def render_markdown(match: MatchInput, board: QimenBoard, reading: FootballReading) -> str:
    rows = []
    for palace in (4, 9, 2, 3, 5, 7, 8, 1, 6):
        state = board.palaces[palace]
        flags = "、".join(
            flag for flag, active in (("旬空", state.is_void), ("驛馬", state.is_horse)) if active
        ) or "—"
        rows.append(
            f"| {state.name} | {'/'.join(state.heaven_stems) or '—'} | "
            f"{state.earth_stem}{('/' + '/'.join(state.earth_hidden_stems)) if state.earth_hidden_stems else ''} | "
            f"{'/'.join(state.stars) or '—'} | {state.door or '—'} | {state.deity or '—'} | {flags} |"
        )

    scenario_lines = []
    for scenario in reading.scenarios:
        scenario_lines.append(
            f"{scenario.rank}. **{scenario.title}**（排序索引 {scenario.signal_index}）  \n"
            f"   依據：{'；'.join(scenario.basis)}  \n"
            f"   邊界：{scenario.boundary}"
        )

    pattern_lines = [
        f"- {hit.name}｜{hit.condition}｜{hit.reading}｜注意：{hit.caution}"
        for hit in board.patterns
    ] or ["- 本盤未命中目前版本可自動判定的格局。"]

    return "\n".join([
        "# 奇門遁甲足球賽前研究報告",
        "",
        f"- 賽事：{match.home_team} vs {match.away_team}",
        f"- 賽事／場地：{match.competition}｜{match.venue}，{match.city}",
        f"- 開賽：{match.event_at.isoformat()}（{match.timezone_name}）",
        f"- freeze_at：{match.freeze_at.isoformat()}",
        f"- 口徑：{match.scope}",
        f"- 完整性：{match.integrity_status()['overall']}",
        "",
        "## 起局方法",
        "",
        f"{board.method.family}／{board.method.plate_method}／{board.method.ju_method}；"
        f"{board.method.center_policy}；版本 `{board.method.version}`。",
        "",
        f"四柱：{board.calendar.year_ganzhi}年、{board.calendar.month_ganzhi}月、"
        f"{board.calendar.day_ganzhi}日、{board.calendar.hour_ganzhi}時。",
        f"節氣：{board.calendar.solar_term}（{board.calendar.solar_term_at.isoformat()}）｜"
        f"{board.ju_label}・{board.yuan}；旬首 {board.hour_xun}／{board.xun_head_instrument}。",
        f"值符：{board.chief_star}落{board.chief_star_palace}宮；"
        f"值使：{board.chief_door}落{board.chief_door_palace}宮。",
        "",
        "## 九宮盤",
        "",
        "| 宮 | 天盤干 | 地盤干 | 九星 | 八門 | 八神 | 狀態 |",
        "|---|---|---|---|---|---|---|",
        *rows,
        "",
        "## 自動命中的結構",
        "",
        *pattern_lines,
        "",
        "## 足球應用層",
        "",
        f"主隊固定取日干：{reading.home.stem}／{reading.home.palace_name}；"
        f"客隊固定取時干：{reading.away.stem}／{reading.away.palace_name}。",
        "",
        *scenario_lines,
        "",
        f"> {reading.disclaimer}",
        "",
        "## 可重現性警告",
        "",
        *[f"- {warning}" for warning in board.warnings],
    ])


def render_html(markdown_text: str) -> str:
    """Create a dependency-free, readable HTML export (not a full Markdown parser)."""

    escaped = escape(markdown_text)
    return """<!doctype html>
<html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>奇門遁甲足球賽前研究報告</title>
<style>body{font-family:system-ui,-apple-system,sans-serif;max-width:1000px;margin:2rem auto;padding:0 1rem;line-height:1.65;color:#172033}pre{white-space:pre-wrap;background:#f7f5ef;border:1px solid #ded8c8;border-radius:12px;padding:1.5rem}</style>
</head><body><pre>""" + escaped + "</pre></body></html>"
