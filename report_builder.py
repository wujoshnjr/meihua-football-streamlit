from __future__ import annotations

from typing import Any

from evaluation import final_scores, normalize_score
from knowledge_loader import load_hexagrams, load_trigrams
from models import AIAnalysis, HexagramResult, MatchInput, RulePrediction, SimilarCase


def _score_text(score: tuple[int, int]) -> str:
    return f"{score[0]}-{score[1]}"


def _bullets(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items) if items else "- 無"


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
    trigrams = load_trigrams()
    hexagrams = load_hexagrams()
    final = final_scores(rule_prediction, ai_analysis, len(similar_cases))
    body_tri = trigrams[result.body_gua]
    use_tri = trigrams[result.use_gua]
    main = hexagrams[result.main_hexagram]
    mutual = hexagrams[result.mutual_hexagram]
    changed = hexagrams[result.changed_hexagram]

    similar_md: list[str] = []
    for case in similar_cases:
        similar_md.append(
            f"### {case.case_id}｜{case.match_name}\n"
            f"- 綜合相似度：{case.similarity:.3f}\n"
            f"- 結構相似度：{case.structural_similarity:.3f}\n"
            f"- 文字相似度：{case.text_similarity:.3f}\n"
            f"- 舊預測：{case.predicted_scores or '未記錄'}\n"
            f"- 實際比分：{case.actual_score or '未記錄'}\n"
            f"- 可比共同點：{'；'.join(case.common_points) or '資料不足'}\n"
            f"- 重要差異：{'；'.join(case.differences) or '資料不足'}\n"
            f"- 校準原因：{case.calibration_reason or case.lesson_summary or '未記錄'}"
        )

    ai_section = "## 十、GitHub Models AI 綜合推理\n\n- 本次未呼叫 AI；以固定起卦與本地相似案例引擎為主。"
    if ai_analysis:
        if ai_analysis.ok:
            candidate_lines = []
            for index, score in enumerate(ai_analysis.scores, start=1):
                confidence = ai_analysis.confidences[index - 1] if index - 1 < len(ai_analysis.confidences) else 0.0
                reason = ai_analysis.score_reasons[index - 1] if index - 1 < len(ai_analysis.score_reasons) else ""
                candidate_lines.append(f"- 第{index}選：{_score_text(score)}｜信心 {confidence:.2f}｜{reason}")
            case_lines = []
            for item in ai_analysis.similar_case_analysis:
                case_lines.append(
                    f"- {item.get('case_id', '')}：可用教訓＝{item.get('usable_lesson', '')}；"
                    f"重要差異＝{item.get('important_difference', '')}"
                )
            ai_section = (
                "## 十、GitHub Models AI 綜合推理\n\n"
                f"- 模型：{ai_analysis.model}\n"
                f"- 方向：{ai_analysis.direction}\n"
                + "\n".join(candidate_lines)
                + f"\n- 整體摘要：{ai_analysis.overall_reasoning}\n"
                + f"- 風險提醒：{ai_analysis.risk_warning}\n\n"
                + "### AI 對相似案例的使用方式\n"
                + ("\n".join(case_lines) if case_lines else "- 無")
                + "\n\n### 待賽後驗證\n"
                + _bullets(ai_analysis.calibration_suggestions)
            )
        else:
            ai_section = (
                "## 十、GitHub Models AI 綜合推理\n\n"
                f"- AI 呼叫失敗：{ai_analysis.error}\n"
                "- 系統已自動退回固定規則與本地相似案例引擎，不影響起卦結果。"
            )

    postmatch_section = "## 十一、賽後校準\n\n- 尚未填入實際90分鐘比分。"
    normalized_actual = normalize_score(actual_score)
    if normalized_actual:
        postmatch_section = (
            "## 十一、賽後校準\n\n"
            f"- 實際90分鐘比分：{normalized_actual}\n"
            f"- 人工校準原因：{calibration_reason or '未填'}\n"
            f"- 校準摘要：{calibration_summary or '未產生'}"
        )
        if postmatch_ai:
            postmatch_section += (
                "\n\n### AI 賽後建議（需人工確認）\n"
                f"- 命中狀態：{postmatch_ai.get('accuracy_summary', '')}\n"
                f"- 錯誤類型：{postmatch_ai.get('error_type', '')}\n"
                f"- 卦象原因：{postmatch_ai.get('hexagram_cause', '')}\n"
                f"- 可泛化教訓：{postmatch_ai.get('generalizable_lesson', '')}\n"
                f"- 不宜泛化因素：{postmatch_ai.get('non_generalizable_factors', '')}\n"
                f"- 建議規則：{postmatch_ai.get('rule_candidate', '')}"
            )

    return f"""# {match.match_name}｜梅花易數足球 AI 報告

> 判斷範圍：{match.scope}  
> 資料原則：只使用賽前資料；歷史案例僅供結構校準，不得倒灌本場賽果。  
> 系統版本：{result.calculation_version} / {rule_prediction.method}

---

## 一、比賽設定

- 賽事：{match.competition or '未填'}
- 體方：{match.body_team}
- 用方：{match.use_team}
- 賽前偏向：{match.prematch_leaning or '未特別填寫'}
- 判斷範圍：{match.scope}

## 二、起卦取數

- 體方段字數：{result.body_count} → {result.body_gua}（數{result.body_number}，五行{result.body_element}）
- 用方段字數：{result.use_count} → {result.use_gua}（數{result.use_number}，五行{result.use_element}）
- 完整段落總字數：{result.total_count} → 第{result.moving_line}爻動
- 動爻位置：{result.moving_side}／{result.moving_layer}

## 三、整體卦勢鏈

- 本卦：{result.main_hexagram}
- 互卦：{result.mutual_hexagram}
- 動爻：第{result.moving_line}爻，在{result.moving_side}
- 體方轉象：{result.body_transition}
- 用方轉象：{result.use_transition}
- 變卦：{result.changed_hexagram}
- 體用生剋：{result.relation}

{result.relation_detail}

{result.moving_detail}

## 四、八卦詳細解讀

### 體卦：{result.body_gua}

- 自然象：{body_tri['symbol']}；{body_tri['nature']}
- 足球象：{body_tri['football']}
- 進攻：{body_tri['attack']}
- 防守：{body_tri['defense']}
- 節奏：{body_tri['tempo']}
- 進球折算：{body_tri['goal_rule']}

### 用卦：{result.use_gua}

- 自然象：{use_tri['symbol']}；{use_tri['nature']}
- 足球象：{use_tri['football']}
- 進攻：{use_tri['attack']}
- 防守：{use_tri['defense']}
- 節奏：{use_tri['tempo']}
- 進球折算：{use_tri['goal_rule']}

## 五、本卦、互卦、變卦

### 本卦：{result.main_hexagram}

- 核心：{main['core']}
- 足球：{main['football']}
- 開局：{main['opening']}
- 中段：{main['middle']}
- 終局風險：{main['risk']}

### 互卦：{result.mutual_hexagram}

- 核心：{mutual['core']}
- 足球：{mutual['football']}
- 中段：{mutual['middle']}
- 風險：{mutual['risk']}

### 變卦：{result.changed_hexagram}

- 核心：{changed['core']}
- 足球：{changed['football']}
- 後段：{changed['ending']}
- 風險：{changed['risk']}

## 六、足球先驗 × 卦象有界修正引擎

- 純足球基線 λ：{match.body_team} {rule_prediction.football_expected_body_goals:.2f}｜{match.use_team} {rule_prediction.football_expected_use_goals:.2f}
- 卦象修正倍率：體方 ×{rule_prediction.hexagram_body_multiplier:.3f}｜用方 ×{rule_prediction.hexagram_use_multiplier:.3f}｜上限 ±{rule_prediction.hexagram_adjustment_cap:.0%}
- 修正後 λ：{match.body_team} {rule_prediction.expected_body_goals:.2f}｜{match.use_team} {rule_prediction.expected_use_goals:.2f}
- 方向：{rule_prediction.direction}
- 信心：{rule_prediction.confidence:.3f}
- 首選：{_score_text(rule_prediction.scores[0])}
- 第二選：{_score_text(rule_prediction.scores[1])}
- 第三選：{_score_text(rule_prediction.scores[2])}

### 規則理由

{_bullets(rule_prediction.reasons)}

### 命中的校準規則

{_bullets([f"{rule['id']}｜{rule['name']}｜狀態 {rule.get('status', '')}｜實際權重 {float(rule.get('applied_scale', 0.0)):.0%}：{rule['lesson']}" for rule in rule_prediction.matched_rules])}

## 七、本地相似案例引擎

{chr(10).join(similar_md) if similar_md else '- 尚無具備實際比分或校準原因的可用歷史案例。'}

## 八、最終三個比分

- 首選：{_score_text(final[0])}
- 第二選：{_score_text(final[1])}
- 第三選：{_score_text(final[2])}

## 九、結構標籤

{_bullets(result.structural_tags)}

{ai_section}

{postmatch_section}

---

## 十二、賽前原始文字

### 體方段落

{match.body_text}

### 用方段落

{match.use_text}

### 完整賽前中性段落

{match.full_text}

### 賽前補充資料

{match.context_notes or '未填'}
"""
