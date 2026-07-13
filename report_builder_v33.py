from __future__ import annotations

from typing import Any

from evaluation import controlled_final_scores
from models import AIAnalysis, HexagramResult, MatchInput, RulePrediction, SimilarCase
from report_builder import build_markdown_report as build_v32_report


def build_markdown_report(
    match: MatchInput,
    result: HexagramResult,
    rule_prediction: RulePrediction,
    similar_cases: list[SimilarCase],
    ai_analysis: AIAnalysis | None = None,
    actual_score: str = "",
    calibration_reason: str = "",
    calibration_summary: str = "",
    postmatch_ai: dict[str, Any] | None = None,
) -> str:
    base = build_v32_report(
        match,
        result,
        rule_prediction,
        similar_cases,
        ai_analysis=ai_analysis,
        actual_score=actual_score,
        calibration_reason=calibration_reason,
        calibration_summary=calibration_summary,
        postmatch_ai=postmatch_ai,
    )
    final, control = controlled_final_scores(rule_prediction, ai_analysis, len(similar_cases))
    probabilities = rule_prediction.outcome_probabilities or {}
    final_text = "、".join(f"{a}-{b}" for a, b in final)
    diagnostics = "\n".join(f"- {item}" for item in rule_prediction.diagnostics) or "- 無"
    script = rule_prediction.hexagram_script or {}
    script_reasons = "\n".join(f"- {item}" for item in script.get("reasons", [])) or "- 無"
    numeric_signals = "\n".join(
        f"- {item.get('formula', '')} → {item.get('value', '')}：{item.get('reason', '')}"
        for item in script.get("numeric_signals", [])
    ) or "- 無符合門檻的卦數錨點"
    script_candidates = "\n".join(
        f"- {item.get('score', '')}（{item.get('archetype', '')}，強度{float(item.get('script_strength', 0)):.2f}）：{item.get('reason', '')}"
        for item in script.get("candidate_scores", [])
    ) or "- 無"
    semantic_evidence = "\n".join(
        f"- **{item.get('stage', '')}｜{item.get('source', '')}**：{item.get('observation', '')} → {item.get('interpretation', '')}"
        for item in script.get("semantic_evidence", [])
    ) or "- 無"
    semantic_scenarios = "\n".join(
        f"- **{item.get('name', '')}**：{item.get('narrative', '')}；成立條件：{'、'.join(item.get('requires', []))}；"
        f"失效條件：{item.get('failure_condition', '')}；成果形狀：{item.get('goal_shape', '')}"
        for item in script.get("scenario_hypotheses", [])
    ) or "- 無"

    ai_audit = "- 本次未呼叫AI。"
    if ai_analysis:
        if ai_analysis.ok:
            football = "；".join(ai_analysis.football_evidence) or "未提供"
            hexagram = "；".join(ai_analysis.hexagram_evidence) or "未提供"
            deliberation = ai_analysis.hexagram_deliberation or {}
            primary_scenario = deliberation.get("primary_scenario", {})
            alternative_scenario = deliberation.get("alternative_scenario", {})
            ai_audit = (
                f"#### 第一階段：盲解卦（未見比分、機率、λ與實力分）\n\n"
                f"- 盲解模型：{deliberation.get('model', '未記錄')}\n"
                f"- 核心論點：{deliberation.get('thesis', '未提供')}\n"
                f"- 核心矛盾：{deliberation.get('primary_conflict', '未提供')}\n"
                f"- 開局：{deliberation.get('opening_phase', '未提供')}\n"
                f"- 中段：{deliberation.get('middle_phase', '未提供')}\n"
                f"- 動爻轉折：{deliberation.get('turning_point', '未提供')}\n"
                f"- 終局：{deliberation.get('ending_phase', '未提供')}\n"
                f"- 體方破門路徑：{deliberation.get('body_scoring_path', '未提供')}\n"
                f"- 用方破門路徑：{deliberation.get('use_scoring_path', '未提供')}\n"
                f"- 主劇本〔{primary_scenario.get('name', '')}〕：{primary_scenario.get('narrative', '')}\n"
                f"- 替代劇本〔{alternative_scenario.get('name', '')}〕：{alternative_scenario.get('narrative', '')}\n"
                f"- 反解：{deliberation.get('counter_reading', '未提供')}\n\n"
                f"#### 第二階段：足球校準與比分決策\n\n"
                f"- 採用劇本：{'、'.join(ai_analysis.selected_scenario_names) or '未提供'}\n"
                f"- AI體方實力分：{ai_analysis.body_strength_score:.1f}\n"
                f"- AI用方實力分：{ai_analysis.use_strength_score:.1f}\n"
                f"- 證據品質：{ai_analysis.evidence_quality:.2f}\n"
                f"- 方向信心：{ai_analysis.direction_confidence:.2f}\n"
                f"- 足球證據：{football}\n"
                f"- 卦象證據：{hexagram}\n"
                f"- 矛盾警告：{ai_analysis.contradiction_warning or '無'}\n"
                f"- 連續劇本：{ai_analysis.match_script_summary or '未提供'}\n"
                f"- 開局：{ai_analysis.opening_phase or '未提供'}\n"
                f"- 中段：{ai_analysis.middle_phase or '未提供'}\n"
                f"- 終局：{ai_analysis.ending_phase or '未提供'}\n"
                f"- 破門通道：{ai_analysis.scoring_channel_analysis or '未提供'}\n"
                f"- 能量歸屬：{ai_analysis.energy_ownership_analysis or '未提供'}\n"
                f"- 總球推理：{ai_analysis.total_goals_reasoning or '未提供'}\n"
                f"- 比分分配：{ai_analysis.score_allocation_reasoning or '未提供'}"
            )
        else:
            ai_audit = f"- AI不可用：{ai_analysis.error}"

    audit = f"""

---

## 十三、v4.2 語義卦線、盲解卦與決策審計

### 本地語義卦線（先於任何比分決策）

{script.get('semantic_story', '')}

#### 主解

{script.get('primary_interpretation', '')}

#### 反解與失效條件

{script.get('counter_interpretation', '')}

- 體方破門路徑：{script.get('body_scoring_path', '')}
- 用方破門路徑：{script.get('use_scoring_path', '')}
- 動爻轉折：{script.get('turning_point', '')}
- 終局邏輯：{script.get('ending_logic', '')}

#### 語義證據鏈

{semantic_evidence}

#### 預先保留的劇本分支

{semantic_scenarios}

### 賽前足球先驗（不參與起卦字數）

- 體方實力：{match.body_strength_rating:.1f}
- 用方實力：{match.use_strength_rating:.1f}
- 先驗可信度：{match.prior_confidence:.0%}
- 場地：{match.venue}
- 純足球體方 λ：{rule_prediction.football_expected_body_goals:.3f}
- 純足球用方 λ：{rule_prediction.football_expected_use_goals:.3f}

### 卦象有界修正

- 體方倍率：{rule_prediction.hexagram_body_multiplier:.3f}
- 用方倍率：{rule_prediction.hexagram_use_multiplier:.3f}
- 單方修正上限：±{rule_prediction.hexagram_adjustment_cap:.0%}
- 修正後體方 λ：{rule_prediction.expected_body_goals:.3f}
- 修正後用方 λ：{rule_prediction.expected_use_goals:.3f}

### 量化劇本審計（不是解卦本身）

- 劇本版本：{script.get('version', '')}
- 比賽環境：{script.get('environment', '')}
- 能量走勢：{script.get('trajectory', '')}
- 開局／本卦：{script.get('opening_reading', '')}
- 中段／互卦：{script.get('middle_reading', '')}
- 動爻至終局：{script.get('ending_reading', '')}
- 全線摘要：{script.get('energy_flow_summary', '')}
- 比賽動能：{float(script.get('dynamics_score', 0)):.1f}/100
- 破門通道：{float(script.get('scoring_channel_score', 0)):.1f}/100
- 終局收束：{float(script.get('closure_score', 0)):.1f}/100
- 反轉波動：{float(script.get('volatility_score', 0)):.1f}/100
- 能量歸屬：體{float(script.get('body_ownership', 0)):.1f}／用{float(script.get('use_ownership', 0)):.1f}
- 完成通道：體{float(script.get('body_finishing', 0)):.1f}／用{float(script.get('use_finishing', 0)):.1f}
- 鏡像判定：{script.get('mirror_mode', '無')}
- 零球閘門：{'開' if script.get('zero_goal_gate') else '關'}
- 高比分閘門：{'開' if script.get('high_score_gate') else '關'}
- 雙方進球訊號：{'是' if script.get('btts_signal') else '否'}
- 大勝方：{script.get('rout_side') or '無'}
- 單向破門方：{script.get('one_sided_side') or '無'}
- 總球錨點：{script.get('total_goal_targets', [])}
- 劇本混合權重：{rule_prediction.scenario_weight:.0%}
- 劇本期望進球：體{rule_prediction.scenario_expected_body_goals:.3f}／用{rule_prediction.scenario_expected_use_goals:.3f}

#### 卦數次級錨點

{numeric_signals}

#### 劇本候選比分

{script_candidates}

#### 劇本觸發理由

{script_reasons}

### 規則勝平負機率

- 體方勝：{probabilities.get('體方勝', 0.0):.1%}
- 平局：{probabilities.get('平局', 0.0):.1%}
- 用方勝：{probabilities.get('用方勝', 0.0):.1%}

### 系統診斷

{diagnostics}

### AI兩階段證據分離

{ai_audit}

### 最終控制

- 模式：{control.get('mode', '')}
- AI權重：{float(control.get('ai_weight', 0.0)):.0%}
- 方向保護：{'是' if control.get('direction_guard') else '否'}
- 控制說明：{control.get('note', '')}
- 最終三選：{final_text}

> v4.2 原則：先保存本→互→動→變的語義卦線與反解。AI第一階段完全看不到比分池、機率、λ、實力分與歷史比分；第二階段才以足球先驗校準並從中性候選池決策。數值只作有界校驗，不得反過來取代解卦。單場賽果產生的規則保持假說、權重為零；任何賽後資料不得改寫已鎖定的賽前版本。
"""
    return base + audit
