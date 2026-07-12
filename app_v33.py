from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from ai_reasoner_v33 import GitHubModelsClient, PROMPT_VERSION, run_ai_prediction
from calibration_center import render_calibration_center
from case_memory import retrieve_similar_cases
from config import load_config
from evaluation import controlled_final_scores
from knowledge_loader import load_calibration_rules, load_hexagrams, load_trigrams
from meihua_engine import calculate_match_hexagram
from metrics_dashboard import render_metrics_dashboard
from models import AIAnalysis, MatchInput
from report_builder_v33 import build_markdown_report
from score_engine import predict_scores
from storage_v33 import CaseStore, build_case_row, save_report, safe_filename
from version import APP_TITLE, APP_VERSION


def _score_text(score: tuple[int, int]) -> str:
    return f"{score[0]}-{score[1]}"


def _load_config_and_store() -> tuple[Any, CaseStore]:
    try:
        secrets = dict(st.secrets)
    except Exception:
        secrets = {}
    config = load_config(secrets)
    return config, CaseStore(config)


def _load_casebook(store: CaseStore, force: bool = False) -> pd.DataFrame:
    if force or "casebook_df" not in st.session_state:
        try:
            st.session_state["casebook_df"] = store.load()
            st.session_state.pop("casebook_error", None)
        except Exception as exc:
            st.session_state["casebook_df"] = pd.DataFrame()
            st.session_state["casebook_error"] = str(exc)
    return st.session_state["casebook_df"]


def _validate_match(match: MatchInput) -> list[str]:
    fields = {
        "比賽名稱": match.match_name,
        "體方": match.body_team,
        "用方": match.use_team,
        "體方段落": match.body_text,
        "用方段落": match.use_text,
        "完整賽前中性介紹段落": match.full_text,
    }
    return [name for name, value in fields.items() if not str(value).strip()]


def _current_ai_model(config: Any) -> str:
    return str(st.session_state.get("ai_model_override", config.ai_model)).strip() or config.ai_model


def _render_sidebar(config: Any, store: CaseStore) -> None:
    with st.sidebar:
        st.header("系統與後台")
        if config.use_github_backend:
            st.success(f"GitHub案例後台：{config.github_repo} / {config.github_branch}")
        else:
            st.warning("GitHub案例後台未啟用，目前只寫入Streamlit暫存空間。")

        if config.use_ai:
            st.success("GitHub Models AI：已啟用（證據融合）")
            st.text_input("AI模型ID", value=config.ai_model, key="ai_model_override")
            if st.button("測試AI連線與模型", width="stretch"):
                try:
                    client = GitHubModelsClient(
                        token=config.github_models_token,
                        model=_current_ai_model(config),
                        timeout=config.request_timeout_seconds,
                        max_tokens=500,
                        temperature=0.0,
                    )
                    ids = {str(item.get("id", "")) for item in client.list_models()}
                    if _current_ai_model(config) in ids:
                        st.success(f"連線成功：{_current_ai_model(config)}")
                    else:
                        st.warning(f"連線成功，但catalog未找到目前模型；共讀到{len(ids)}個模型。")
                except Exception as exc:
                    st.error(str(exc))
        else:
            st.info("GitHub Models AI尚未啟用；v4.1足球先驗×連續卦象劇本引擎與相似案例仍可運作。")

        if st.button("重新讀取GitHub案例庫", width="stretch"):
            _load_casebook(store, force=True)
            st.rerun()
        st.caption("v4.1：足球先驗先建λ＋連續卦象劇本＋情境比分重排＋不可覆寫的賽前鎖定。")


def _render_prior_help() -> None:
    st.info(
        "賽前實力先驗只使用開賽前可知資訊，例如排名、陣容完整度、近期狀態、傷停與場地。"
        "50/50代表完全中性；它會先建立純足球期望進球λ，不參與任何起卦字數，也不能因為你支持某隊就自動提高。"
    )


def _render_prematch(config: Any, store: CaseStore, casebook_df: pd.DataFrame) -> None:
    st.subheader("賽前預測")
    st.caption("固定起卦與足球先驗分離；支持隊只決定體方，所有輸出固定判斷90分鐘。")

    with st.form("prematch_prediction_form_v33", clear_on_submit=False):
        c1, c2 = st.columns(2)
        with c1:
            competition = st.text_input("賽事", value="世界盃")
            match_name = st.text_input("比賽名稱", value="法國 vs 摩洛哥")
            body_team = st.text_input("體方", value="法國")
        with c2:
            use_team = st.text_input("用方", value="摩洛哥")
            prematch_leaning = st.text_input("賽前偏向", value="看好法國，因此法國為體")
            save_mode = st.radio("案例儲存模式", ["自動更新", "強制新增"], horizontal=True)

        scope = st.selectbox("判斷範圍", ["90分鐘，不含延長賽與PK"], index=0)
        with st.expander("賽前足球先驗（不參與起卦字數）", expanded=True):
            p1, p2, p3 = st.columns(3)
            with p1:
                body_strength_rating = st.slider("體方賽前實力", 0, 100, 50, 1)
            with p2:
                use_strength_rating = st.slider("用方賽前實力", 0, 100, 50, 1)
            with p3:
                prior_confidence = st.slider("先驗可信度", 0.0, 1.0, 0.50, 0.05)
            venue = st.selectbox("場地", ["中立場", "體方主場", "用方主場"], index=0)
            st.caption("請依賽前客觀資料填寫，不要把支持或賽後結果當成實力評分。")

        body_text = st.text_area("體方段落", height=170)
        use_text = st.text_area("用方段落", height=170)
        full_text = st.text_area("完整賽前中性介紹段落（用來算動爻）", height=230)
        context_notes = st.text_area("賽前補充資料（只輔助解卦，不參與字數）", height=120)
        submitted = st.form_submit_button("固定起卦並建立v4.1預測", type="primary", width="stretch")

    match = MatchInput(
        match_name=match_name,
        competition=competition,
        body_team=body_team,
        use_team=use_team,
        body_text=body_text,
        use_text=use_text,
        full_text=full_text,
        scope=scope,
        prematch_leaning=prematch_leaning,
        context_notes=context_notes,
        body_strength_rating=float(body_strength_rating),
        use_strength_rating=float(use_strength_rating),
        prior_confidence=float(prior_confidence),
        venue=venue,
    )

    if submitted:
        missing = _validate_match(match)
        if missing:
            st.error("請先補齊：" + "、".join(missing))
        else:
            try:
                result = calculate_match_hexagram(match)
                rule_prediction = predict_scores(result, match)
                similar_cases = retrieve_similar_cases(
                    result,
                    casebook_df,
                    top_k=config.ai_top_k_cases,
                    max_rows=config.max_casebook_rows_for_ai,
                )
                st.session_state["match_input"] = match
                st.session_state["hexagram_result"] = result
                st.session_state["rule_prediction"] = rule_prediction
                st.session_state["similar_cases"] = similar_cases
                st.session_state["save_mode"] = save_mode
                st.session_state.pop("ai_analysis", None)
                st.success("足球基線λ、固定起卦、連續卦象劇本與已確認案例搜尋完成。")
            except Exception as exc:
                st.exception(exc)

    if "hexagram_result" not in st.session_state:
        _render_prior_help()
        return

    saved_match: MatchInput = st.session_state["match_input"]
    result = st.session_state["hexagram_result"]
    rule_prediction = st.session_state["rule_prediction"]
    similar_cases = st.session_state.get("similar_cases", [])
    ai_analysis: AIAnalysis | None = st.session_state.get("ai_analysis")

    st.markdown("### 一、純足球先驗基線")
    baseline_scores = rule_prediction.football_only_scores
    b1, b2, b3, b4 = st.columns(4)
    b1.metric("基線首選", _score_text(baseline_scores[0]) if baseline_scores else "—")
    b2.metric("基線第二選", _score_text(baseline_scores[1]) if len(baseline_scores) > 1 else "—")
    b3.metric("基線第三選", _score_text(baseline_scores[2]) if len(baseline_scores) > 2 else "—")
    baseline_probabilities = rule_prediction.football_only_outcome_probabilities or {}
    b4.metric("基線總λ", f"{rule_prediction.football_expected_body_goals + rule_prediction.football_expected_use_goals:.2f}")
    st.caption(
        f"足球λ：{result.body_team}{rule_prediction.football_expected_body_goals:.2f}｜"
        f"{result.use_team}{rule_prediction.football_expected_use_goals:.2f}｜"
        f"體勝{baseline_probabilities.get('體方勝', 0):.1%}／平{baseline_probabilities.get('平局', 0):.1%}／"
        f"用勝{baseline_probabilities.get('用方勝', 0):.1%}；此層完全不使用卦象。"
    )

    st.markdown("### 二、連續卦象劇本後的固定規則")
    r1, r2, r3, r4 = st.columns(4)
    r1.metric("首選", _score_text(rule_prediction.scores[0]))
    r2.metric("第二選", _score_text(rule_prediction.scores[1]))
    r3.metric("第三選", _score_text(rule_prediction.scores[2]))
    r4.metric("方向", rule_prediction.direction)
    probabilities = rule_prediction.outcome_probabilities or {}
    st.caption(
        f"劇本期望進球：{result.body_team}{rule_prediction.scenario_expected_body_goals:.2f}｜"
        f"{result.use_team}{rule_prediction.scenario_expected_use_goals:.2f}｜規則信心{rule_prediction.confidence:.3f}｜"
        f"體勝{probabilities.get('體方勝', 0):.1%}／平{probabilities.get('平局', 0):.1%}／用勝{probabilities.get('用方勝', 0):.1%}｜"
        f"有界λ倍率：體×{rule_prediction.hexagram_body_multiplier:.3f}、用×{rule_prediction.hexagram_use_multiplier:.3f}｜"
        f"劇本權重{rule_prediction.scenario_weight:.0%}"
    )

    for diagnostic in rule_prediction.diagnostics:
        if "衝突" in diagnostic or "過度集中" in diagnostic:
            st.warning(diagnostic)
        else:
            st.info(diagnostic)

    ai_col, note_col = st.columns([1, 2])
    with ai_col:
        can_call = config.use_ai and st.session_state.get("ai_call_count", 0) < 20
        if st.button("讓GitHub Models AI做證據融合", disabled=not can_call, width="stretch"):
            with st.spinner("AI正在分開審查足球證據與卦象證據……"):
                client = GitHubModelsClient(
                    token=config.github_models_token,
                    model=_current_ai_model(config),
                    timeout=config.request_timeout_seconds,
                    max_tokens=config.ai_max_output_tokens,
                    temperature=min(config.ai_temperature, 0.20),
                )
                ai_analysis = run_ai_prediction(client, saved_match, result, rule_prediction, similar_cases)
                st.session_state["ai_analysis"] = ai_analysis
                st.session_state["ai_call_count"] = st.session_state.get("ai_call_count", 0) + 1
                st.success("AI連續劇本審查完成。" if ai_analysis.ok else "AI不可用，已退回v4.1固定引擎。")
    with note_col:
        st.caption(
            "AI候選池固定包含體勝、平局與用勝。普通證據最多移動3位；只有證據品質、方向信心與實力差同時達標，"
            "才能跨方向糾正規則並最多移動6位。"
        )

    ai_analysis = st.session_state.get("ai_analysis")
    chosen_scores, control = controlled_final_scores(rule_prediction, ai_analysis, len(similar_cases))
    st.markdown("### 三、證據融合最終排序")
    f1, f2, f3 = st.columns(3)
    f1.metric("最終首選", _score_text(chosen_scores[0]))
    f2.metric("最終第二選", _score_text(chosen_scores[1]))
    f3.metric("最終第三選", _score_text(chosen_scores[2]))
    st.info(
        f"模式：{control['mode']}｜AI權重{control['ai_weight']:.0%}｜已確認相似案例{len(similar_cases)}場｜"
        f"證據品質{control.get('evidence_quality', 0):.0%}｜方向信心{control.get('direction_confidence', 0):.0%}｜{control['note']}"
    )

    tabs = st.tabs(["起卦全解", "卦線劇本", "規則與校準", "方向審計", "相似案例", "AI證據", "報告與鎖定"])
    with tabs[0]:
        st.markdown(
            "\n".join(
                [
                    "| 項目 | 內容 |",
                    "|---|---|",
                    f"| 體卦 | {result.body_team}＝{result.body_gua}，數{result.body_number}，{result.body_element} |",
                    f"| 用卦 | {result.use_team}＝{result.use_gua}，數{result.use_number}，{result.use_element} |",
                    f"| 本卦 | {result.main_hexagram} |",
                    f"| 互卦 | {result.mutual_hexagram} |",
                    f"| 動爻 | 第{result.moving_line}爻，在{result.moving_side} |",
                    f"| 體方轉象 | {result.body_transition} |",
                    f"| 用方轉象 | {result.use_transition} |",
                    f"| 變卦 | {result.changed_hexagram} |",
                    f"| 體用 | {result.relation} |",
                ]
            )
        )
        st.write(result.relation_detail)
        st.write(result.moving_detail)
        trigrams, hexagrams = load_trigrams(), load_hexagrams()
        left, right = st.columns(2)
        with left:
            st.markdown(f"#### 體卦：{result.body_gua}")
            st.json(trigrams[result.body_gua], expanded=True)
        with right:
            st.markdown(f"#### 用卦：{result.use_gua}")
            st.json(trigrams[result.use_gua], expanded=True)
        for label, name in [("本卦", result.main_hexagram), ("互卦", result.mutual_hexagram), ("變卦", result.changed_hexagram)]:
            with st.expander(f"{label}：{name}", expanded=(label == "本卦")):
                st.write(hexagrams[name])

    with tabs[1]:
        script = rule_prediction.hexagram_script or {}
        st.subheader(str(script.get("environment", "連續卦象劇本")))
        st.info(str(script.get("energy_flow_summary", "尚無劇本摘要。")))
        d1, d2, d3, d4 = st.columns(4)
        d1.metric("比賽動能", f"{float(script.get('dynamics_score', 0)):.0f}/100")
        d2.metric("破門通道", f"{float(script.get('scoring_channel_score', 0)):.0f}/100")
        d3.metric("終局收束", f"{float(script.get('closure_score', 0)):.0f}/100")
        d4.metric("反轉波動", f"{float(script.get('volatility_score', 0)):.0f}/100")
        st.markdown(
            "\n".join(
                [
                    "| 時段 | 連續解讀 |",
                    "|---|---|",
                    f"| 開局／本卦 | {script.get('opening_reading', '')} |",
                    f"| 中段／互卦 | {script.get('middle_reading', '')} |",
                    f"| 動爻至終局 | {script.get('ending_reading', '')} |",
                ]
            )
        )
        o1, o2, o3, o4 = st.columns(4)
        o1.metric("體方能量歸屬", f"{float(script.get('body_ownership', 0)):.0f}")
        o2.metric("用方能量歸屬", f"{float(script.get('use_ownership', 0)):.0f}")
        o3.metric("體方完成通道", f"{float(script.get('body_finishing', 0)):.0f}")
        o4.metric("用方完成通道", f"{float(script.get('use_finishing', 0)):.0f}")
        st.write(
            f"走勢：{script.get('trajectory', '')}｜鏡像：{script.get('mirror_mode', '無')}｜"
            f"總球錨點：{script.get('total_goal_targets', [])}"
        )
        st.write(
            f"零球閘門：{'開' if script.get('zero_goal_gate') else '關'}｜"
            f"高比分閘門：{'開' if script.get('high_score_gate') else '關'}｜"
            f"雙方進球：{'是' if script.get('btts_signal') else '否'}｜"
            f"大勝方：{script.get('rout_side') or '無'}｜單向破門：{script.get('one_sided_side') or '無'}"
        )
        numeric_signals = script.get("numeric_signals", [])
        if numeric_signals:
            st.write("#### 卦數次級錨點")
            for signal in numeric_signals:
                st.write(f"- {signal.get('formula', '')} → {signal.get('value', '')}：{signal.get('reason', '')}")
        st.write("#### 劇本比分候選")
        candidate_rows = ["| 比分 | 劇本 | 強度 | 觸發理由 |", "|---:|---|---:|---|"]
        for candidate in script.get("candidate_scores", []):
            candidate_rows.append(
                f"| {candidate.get('score', '')} | {candidate.get('archetype', '')} | "
                f"{float(candidate.get('script_strength', 0)):.2f} | {candidate.get('reason', '')} |"
            )
        st.markdown("\n".join(candidate_rows))

    with tabs[2]:
        for reason in rule_prediction.reasons:
            st.write("- " + reason)
        if rule_prediction.matched_rules:
            for rule in rule_prediction.matched_rules:
                st.info(f"{rule['id']}｜{rule['name']}\n\n{rule['lesson']}")
        else:
            st.write("本場未完全命中特定校準規則。")
        score_rows = ["| 排名 | 比分 | 機率 | 方向 | 樣式倍率 |", "|---:|---:|---:|---|---:|"]
        for row in rule_prediction.score_grid[:24]:
            score_rows.append(
                f"| {int(row.get('rank', 0))} | {row.get('score', '')} | "
                f"{float(row.get('probability', 0.0)):.2%} | {row.get('outcome', '')} | "
                f"{float(row.get('pattern_multiplier', 1.0)):.3f} |"
            )
        st.markdown("\n".join(score_rows))

    with tabs[3]:
        st.write("#### 人工賽前先驗")
        st.json(rule_prediction.football_prior, expanded=True)
        st.write("#### 規則勝平負機率")
        st.json(rule_prediction.outcome_probabilities, expanded=True)
        st.write("#### 系統警訊")
        for diagnostic in rule_prediction.diagnostics:
            st.write("- " + diagnostic)
        st.write("#### AI控制紀錄")
        st.json(control, expanded=True)

    with tabs[4]:
        st.caption("只有實際比分、校準原因完整，且校準狀態為已確認的案例才會影響下一場。")
        if not similar_cases:
            st.warning("目前沒有可用的已確認相似案例。")
        for case in similar_cases:
            with st.expander(f"{case.case_id}｜{case.match_name}｜相似度{case.similarity:.3f}"):
                st.write(f"歷史預測：{case.predicted_scores or '未記錄'}｜實際：{case.actual_score or '未記錄'}")
                st.write("共同點：" + "；".join(case.common_points))
                st.write("差異：" + "；".join(case.differences))
                st.write("校準：" + (case.calibration_reason or case.lesson_summary or "未記錄"))

    with tabs[5]:
        if ai_analysis is None:
            st.info("尚未呼叫AI。")
        elif not ai_analysis.ok:
            st.error(ai_analysis.error)
        else:
            st.success(f"AI模型：{ai_analysis.model}｜證據融合")
            a1, a2, a3, a4 = st.columns(4)
            a1.metric("體方實力分", f"{ai_analysis.body_strength_score:.1f}")
            a2.metric("用方實力分", f"{ai_analysis.use_strength_score:.1f}")
            a3.metric("證據品質", f"{ai_analysis.evidence_quality:.0%}")
            a4.metric("方向信心", f"{ai_analysis.direction_confidence:.0%}")
            st.write("**足球證據**")
            for item in ai_analysis.football_evidence:
                st.write("- " + item)
            st.write("**卦象證據**")
            for item in ai_analysis.hexagram_evidence:
                st.write("- " + item)
            if ai_analysis.contradiction_warning:
                st.warning(ai_analysis.contradiction_warning)
            if ai_analysis.match_script_summary:
                st.write("**AI連續比賽劇本**")
                st.info(ai_analysis.match_script_summary)
                st.write(f"開局：{ai_analysis.opening_phase}")
                st.write(f"中段：{ai_analysis.middle_phase}")
                st.write(f"終局：{ai_analysis.ending_phase}")
                st.write(f"破門通道：{ai_analysis.scoring_channel_analysis}")
                st.write(f"能量歸屬：{ai_analysis.energy_ownership_analysis}")
                st.write(f"總球判斷：{ai_analysis.total_goals_reasoning}")
                st.write(f"比分分配：{ai_analysis.score_allocation_reasoning}")
            for index, score in enumerate(ai_analysis.scores, 1):
                reason = ai_analysis.score_reasons[index - 1] if index - 1 < len(ai_analysis.score_reasons) else ""
                st.write(f"第{index}選{_score_text(score)}：{reason}")
            st.write(ai_analysis.overall_reasoning)
            st.warning(ai_analysis.risk_warning or "無額外風險提醒")

    with tabs[6]:
        report = build_markdown_report(saved_match, result, rule_prediction, similar_cases, ai_analysis=ai_analysis)
        st.download_button(
            "下載賽前Markdown報告",
            data=report,
            file_name=safe_filename(result.match_name) + ".md",
            mime="text/markdown",
            width="stretch",
        )
        if st.button("鎖定賽前預測並儲存案例", type="primary", width="stretch"):
            try:
                report_path = save_report(config, result, report)
                row = build_case_row(
                    saved_match,
                    result,
                    rule_prediction,
                    ai_analysis,
                    similar_cases,
                    actual_score="",
                    calibration_reason="",
                    calibration_summary="賽前預測已鎖定，尚未回填實際比分。",
                    confirmed_ai_calibration=False,
                    report_path=report_path,
                )
                updated, action = store.upsert(row, st.session_state.get("save_mode", "自動更新"))
                st.session_state["casebook_df"] = updated
                st.success(f"賽前預測已{action}並鎖定；請賽後到『賽後校準中心』回填結果。")
            except Exception as exc:
                st.exception(exc)


def _render_knowledge() -> None:
    st.subheader("完整知識庫")
    t1, t2, t3 = st.tabs(["八卦", "六十四卦", "校準規則"])
    with t1:
        trigrams = load_trigrams()
        selected = st.selectbox("選擇八卦", list(trigrams.keys()), key="kb_trigram_v33")
        st.json(trigrams[selected], expanded=True)
    with t2:
        hexagrams = load_hexagrams()
        selected = st.selectbox(
            "選擇六十四卦",
            sorted(hexagrams.keys(), key=lambda name: int(hexagrams[name]["sequence"])),
            key="kb_hexagram_v33",
        )
        st.json(hexagrams[selected], expanded=True)
    with t3:
        for rule in load_calibration_rules():
            with st.expander(f"{rule['id']}｜{rule['name']}｜{rule['status']}"):
                st.write("來源：" + rule.get("source_case", ""))
                st.write("教訓：" + rule.get("lesson", ""))
                if str(rule.get("status", "")).lower() == "hypothesis":
                    st.warning("單場賽果產生的待驗證假說：目前預測權重為0，不會直接改動比分。")
                st.json({"conditions": rule.get("conditions", {}), "effects": rule.get("effects", {})})


def run_app() -> None:
    st.set_page_config(page_title=APP_TITLE, page_icon="☯️", layout="wide")
    st.markdown(
        """
        <style>
        .block-container {padding-top: 1.2rem; padding-bottom: 3rem;}
        div[data-testid="stMetric"] {border: 1px solid rgba(128,128,128,.25); padding: .7rem; border-radius: .7rem;}
        </style>
        """,
        unsafe_allow_html=True,
    )
    config, store = _load_config_and_store()
    casebook_df = _load_casebook(store)
    _render_sidebar(config, store)

    st.title(APP_TITLE)
    st.caption(
        f"v{APP_VERSION}：純足球先驗先建立λ，整條卦線依動能、破門通道、歸屬與收束形成可稽核劇本；"
        "比分情境有界混合且賽前版本不可被賽後資料覆寫。僅供研究，不提供投注或真實資金功能。"
    )

    prematch_tab, calibration_tab, metrics_tab, knowledge_tab = st.tabs(["賽前預測", "賽後校準中心", "模型成績", "知識庫"])
    with prematch_tab:
        _render_prematch(config, store, casebook_df)
    with calibration_tab:
        updated = render_calibration_center(config, store, st.session_state.get("casebook_df", casebook_df))
        if updated is not None:
            st.session_state["casebook_df"] = updated
    with metrics_tab:
        render_metrics_dashboard(st.session_state.get("casebook_df", casebook_df))
    with knowledge_tab:
        _render_knowledge()

    st.caption(
        f"Prompt版本：{PROMPT_VERSION}。本系統是研究與紀錄工具，不是投注建議。"
        "只有已確認校準案例才會影響未來相似案例檢索。"
    )
