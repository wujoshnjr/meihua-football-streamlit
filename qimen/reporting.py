from __future__ import annotations

from datetime import datetime
from html import escape
from typing import Any, TYPE_CHECKING

from .football import FootballReading
from .integrity import canonical_json as canonical_json, sha256_payload
from .interpretation import InterpretationGuide
from .models import QimenBoard
from .prediction import PredictionResult
from .protocol import MatchInput

if TYPE_CHECKING:
    from .evaluation import LockedPrediction


def build_bundle(
    match: MatchInput,
    board: QimenBoard,
    reading: FootballReading,
    *,
    guide: InterpretationGuide | None = None,
    locked_at: datetime | None = None,
    prediction: PredictionResult | None = None,
    prediction_lock: LockedPrediction | None = None,
) -> dict[str, Any]:
    """Return one audit-friendly export with data, method and integrity status."""

    lock_check = next(
        (check for check in guide.audit.checks if check.id == "lock_timestamp"),
        None,
    ) if guide else None
    core = {
        "schema_version": "qimen-football-bundle-v2.2.0",
        "match": match.to_dict(),
        "board": board.to_dict(),
        "football_reading": reading.to_dict(),
        "interpretation_guide": guide.to_dict() if guide else None,
        "prediction": prediction.to_dict() if prediction else None,
        "prediction_lock": prediction_lock.to_dict() if prediction_lock else None,
        "locked_at": locked_at.isoformat() if locked_at else None,
        "boundaries": {
            "knowledge_application_separation": True,
            "question_locked_before_cast": bool(lock_check and lock_check.status == "PASS"),
            "prediction_layer_present": prediction is not None,
            "prediction_locked_before_kickoff": prediction_lock is not None,
            "automatic_1x2_argmax": prediction is not None,
            "automatic_winner": prediction is not None,
            "automatic_fixed_score": False,
            "probability_claim": prediction is not None,
            "probability_calibrated": bool(
                prediction and prediction.calibration_status.startswith("CALIBRATED")
            ),
            "qimen_changes_probability": bool(
                prediction and prediction.qimen_mode != "SHADOW_ONLY"
            ),
            "scope": match.scope,
        },
    }
    core["fingerprint_sha256"] = sha256_payload(core)
    return core


def render_markdown(
    match: MatchInput,
    board: QimenBoard,
    reading: FootballReading,
    *,
    guide: InterpretationGuide | None = None,
    prediction: PredictionResult | None = None,
    prediction_lock: LockedPrediction | None = None,
) -> str:
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

    guide_lines: list[str] = []
    if guide:
        guide_lines = [
            "## 起局／解盤鎖定",
            "",
            f"- 固定問題：{guide.question}",
            f"- 足球焦點：{guide.focus_name}（`{guide.focus_id}`）",
            f"- 起局時點：{guide.cast_basis}",
            f"- 鎖定時間：{guide.locked_at or '未提供'}",
            f"- 盤前稽核：{guide.audit.overall}",
            f"- 主隊用神：{guide.home_use_god.original_stem}／{guide.home_use_god.palace_name}",
            f"- 客隊用神：{guide.away_use_god.original_stem}／{guide.away_use_god.palace_name}",
            "",
            "### 全局訊號",
            "",
            *[f"- {item}" for item in guide.global_signals],
            "",
            "### 十層判讀順序",
            "",
            *[f"- {item}" for item in guide.reading_order],
            "",
            f"> {guide.boundary}",
            "",
        ]

    prediction_lines: list[str] = []
    if prediction:
        score_lines = [
            f"- {item.home_goals}–{item.away_goals}：{item.probability:.1%}"
            for item in prediction.top_scorelines
        ]
        prediction_lines = [
            "## JARVIS 機率基準",
            "",
            f"- 模型：`{prediction.model_version}`（{prediction.model_status}）",
            f"- 比分模型：{prediction.score_model}",
            f"- 預測時點：{prediction.forecast_horizon}｜先發狀態：{prediction.lineup_status}",
            f"- 校準：{prediction.calibration_status}",
            f"- 校準 artifact：{prediction.calibration_source or '—'}",
            f"- 奇門模式：{prediction.qimen_mode}（目前不改動機率）",
            f"- 期望進球：主隊 {prediction.expected_home_goals:.2f}｜客隊 {prediction.expected_away_goals:.2f}",
            f"- 1X2：主勝 {prediction.home_win_probability:.1%}｜和局 {prediction.draw_probability:.1%}｜客勝 {prediction.away_win_probability:.1%}",
            f"- 未校準 1X2：主勝 {prediction.raw_home_win_probability:.1%}｜和局 {prediction.raw_draw_probability:.1%}｜客勝 {prediction.raw_away_win_probability:.1%}",
            f"- 機率最高結果：{prediction.predicted_result}｜前兩名差距 {prediction.decision_margin:.1%}",
            f"- 比分矩陣截尾質量：{prediction.score_grid_tail_mass:.6f}",
            f"- 預測鎖定：{'PASS｜' + prediction_lock.locked_at.isoformat() if prediction_lock else '未通過／回溯模式'}",
            f"- 預測指紋：{prediction_lock.fingerprint_sha256 if prediction_lock else '—'}",
            f"- 資料快照指紋：{prediction.provenance['data_snapshot_sha256']}",
            f"- 足球／奇門特徵指紋：{prediction.provenance['football_feature_sha256']}／{prediction.provenance['qimen_feature_sha256']}",
            f"- Git commit：{prediction.provenance['git_commit']}",
            "",
            "### 機率最高的比分候選",
            "",
            *score_lines,
            "",
            "### 資料警告",
            "",
            *[f"- {warning}" for warning in prediction.data_warnings],
            "",
            f"> {prediction.disclaimer}",
            "",
        ]

    def semantic_lines(label, profile):
        meaning = profile.football_meaning
        return [
            f"### {label}完整足球義",
            "",
            f"重點維度：{'、'.join(meaning.football_dimensions)}。",
            "",
            *[f"- {item}" for item in meaning.layer_readings],
            "",
            "可觀察訊號：" + "；".join(meaning.observable_signals) + "。",
            "",
            "反證條件：" + "；".join(meaning.counter_signals) + "。",
            "",
            f"> {meaning.confidence}。{meaning.boundary}",
            "",
        ]

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
        *guide_lines,
        *prediction_lines,
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
        f"九星旺衰：依月支計算；規則版本 `{reading.seasonal_rule_version}`。",
        "",
        *semantic_lines("主隊／日干", reading.home),
        *semantic_lines("客隊／時干", reading.away),
        "### 候選情境排序",
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
