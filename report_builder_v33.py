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
                f"- 矛盾警告：{ai_analysis.contradiction_warning or '無'}"
            )
        else:
            ai_audit = f"- AI不可用：{ai_analysis.error}"

    audit = f"""

---

## 十三、v3.3 決策審計

### 賽前足球先驗（不參與起卦字數）

- 體方實力：{match.body_strength_rating:.1f}
- 用方實力：{match.use_strength_rating:.1f}
- 先驗可信度：{match.prior_confidence:.0%}
- 場地：{match.venue}

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

> v3.3 原則：體用生剋只是一項風險證據；足球先驗、本卦、互卦、動爻、變卦、歷史校準與AI證據必須分層審查，禁止任何單一規則直接決定勝負。
"""
    return base + audit
