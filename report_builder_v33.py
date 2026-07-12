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

    ai_audit = "- 本次未呼叫AI。"
    if ai_analysis:
        if ai_analysis.ok:
            football = "；".join(ai_analysis.football_evidence) or "未提供"
            hexagram = "；".join(ai_analysis.hexagram_evidence) or "未提供"
            ai_audit = (
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

## 十三、v4.1 連續卦象劇本與決策審計

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

### 連續卦象劇本

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

### AI證據分離

{ai_audit}

### 最終控制

- 模式：{control.get('mode', '')}
- AI權重：{float(control.get('ai_weight', 0.0)):.0%}
- 方向保護：{'是' if control.get('direction_guard') else '否'}
- 控制說明：{control.get('note', '')}
- 最終三選：{final_text}

> v4.1 原則：足球先驗先獨立建立 λ；卦象對單方 λ 的修正仍限制在 ±25%，再由可稽核的連續劇本以最高 46% 情境權重重排比分。先判動能與破門通道，再判能量歸屬與收束，最後才選總球與分配比分。單場賽果產生的規則保持假說、權重為零，直到通過留出驗證；任何賽後資料不得改寫已鎖定的賽前版本。
"""
    return base + audit
