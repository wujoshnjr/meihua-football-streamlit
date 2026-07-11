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
            st.info("GitHub Models AI尚未啟用；v3.3規則引擎與相似案例仍可運作。")

        if st.button("重新讀取GitHub案例庫", width="stretch"):
            _load_casebook(store, force=True)
            st.rerun()
        st.caption("v3.3：足球先驗＋分時段卦象＋平衡候選池＋結構化AI證據。")


def _render_prior_help() -> None:
    st.info(
        "賽前實力先驗只使用開賽前可知資訊，例如排名、陣容完整度、近期狀態、傷停與場地。"
        "50/50代表完全中性；它不參與任何起卦字數，也不能因為你支持某隊就自動提高。"
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
        submitted = st.form_submit_button("固定起卦並建立v3.3規則預測", type="primary", width="stretch")

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
                st.success("固定起卦、分時段規則預測、足球先驗與已確認案例搜尋完成。")
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

    st.markdown("### 一、v3.3固定規則預測")
    r1, r2, r3, r4 = st.columns(4)
    r1.metric("首選", _score_text(rule_prediction.scores[0]))
    r2.metric("第二選", _score_text(rule_prediction.scores[1]))
    r3.metric("第三選", _score_text(rule_prediction.scores[2]))
    r4.metric("方向", rule_prediction.direction)
    probabilities = rule_prediction.outcome_probabilities or {}
    st.caption(
        f"期望進球：{result.body_team}{rule_prediction.expected_body_goals:.2f}｜"
        f"{result.use_team}{rule_prediction.expected_use_goals:.2f}｜規則信心{rule_prediction.confidence:.3f}｜"
        f"體勝{probabilities.get('體方勝', 0):.1%}／平{probabilities.get('平局', 0):.1%}／用勝{probabilities.get('用方勝', 0):.1%}"
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
                st.success("AI證據融合完成。" if ai_analysis.ok else "AI不可用，已退回v3.3規則引擎。")
    with note_col:
        st.caption(
            "AI候選池固定包含體勝、平局與用勝。普通證據最多移動3位；只有證據品質、方向信心與實力差同時達標，"
            "才能跨方向糾正規則並最多移動6位。"
        )

    ai_analysis = st.session_state.get("ai_analysis")
    chosen_scores, control = controlled_final_scores(rule_prediction, ai_analysis, len(similar_cases))
    st.markdown("### 二、證據融合最終排序")
    f1, f2, f3 = st.columns(3)
    f1.metric("最終首選", _score_text(chosen_scores[0]))
    f2.metric("最終第二選", _score_text(chosen_scores[1]))
    f3.metric("最終第三選", _score_text(chosen_scores[2]))
    st.info(
        f"模式：{control['mode']}｜AI權重{control['ai_weight']:.0%}｜已確認相似案例{len(similar_cases)}場｜"
        f"證據品質{control.get('evidence_quality', 0):.0%}｜方向信心{control.get('direction_confidence', 0):.0%}｜{control['note']}"
    )

    tabs = st.tabs(["起卦全解", "規則與校準", "方向審計", "相似案例", "AI證據", "報告與鎖定"])
    with tabs[0]:
        st.dataframe(
            pd.DataFrame(
                [
                    {"項目": "體卦", "內容": f"{result.body_team}＝{result.body_gua}，數{result.body_number}，{result.body_element}"},
                    {"項目": "用卦", "內容": f"{result.use_team}＝{result.use_gua}，數{result.use_number}，{result.use_element}"},
                    {"項目": "本卦", "內容": result.main_hexagram},
                    {"項目": "互卦", "內容": result.mutual_hexagram},
                    {"項目": "動爻", "內容": f"第{result.moving_line}爻，在{result.moving_side}"},
                    {"項目": "體方轉象", "內容": result.body_transition},
                    {"項目": "用方轉象", "內容": result.use_transition},
                    {"項目": "變卦", "內容": result.changed_hexagram},
                    {"項目": "體用", "內容": result.relation},
                ]
            ),
            width="stretch",
            hide_index=True,
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
        for reason in rule_prediction.reasons:
            st.write("- " + reason)
        if rule_prediction.matched_rules:
            for rule in rule_prediction.matched_rules:
                st.info(f"{rule['id']}｜{rule['name']}\n\n{rule['lesson']}")
        else:
            st.write("本場未完全命中特定校準規則。")
        st.dataframe(pd.DataFrame(rule_prediction.score_grid[:24]), width="stretch", hide_index=True)

    with tabs[2]:
        st.write("#### 人工賽前先驗")
        st.json(rule_prediction.football_prior, expanded=True)
        st.write("#### 規則勝平負機率")
        st.json(rule_prediction.outcome_probabilities, expanded=True)
        st.write("#### 系統警訊")
        for diagnostic in rule_prediction.diagnostics:
            st.write("- " + diagnostic)
        st.write("#### AI控制紀錄")
        st.json(control, expanded=True)

    with tabs[3]:
        st.caption("只有實際比分、校準原因完整，且校準狀態為已確認的案例才會影響下一場。")
        if not similar_cases:
            st.warning("目前沒有可用的已確認相似案例。")
        for case in similar_cases:
            with st.expander(f"{case.case_id}｜{case.match_name}｜相似度{case.similarity:.3f}"):
                st.write(f"歷史預測：{case.predicted_scores or '未記錄'}｜實際：{case.actual_score or '未記錄'}")
                st.write("共同點：" + "；".join(case.common_points))
                st.write("差異：" + "；".join(case.differences))
                st.write("校準：" + (case.calibration_reason or case.lesson_summary or "未記錄"))

    with tabs[4]:
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
            for index, score in enumerate(ai_analysis.scores, 1):
                reason = ai_analysis.score_reasons[index - 1] if index - 1 < len(ai_analysis.score_reasons) else ""
                st.write(f"第{index}選{_score_text(score)}：{reason}")
            st.write(ai_analysis.overall_reasoning)
            st.warning(ai_analysis.risk_warning or "無額外風險提醒")

    with tabs[5]:
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
                st.json({"conditions": rule.get("conditions", {}), "effects": rule.get("effects", {})})


def run_app() -> None:
    st.set_page_config(page_title="梅花易數足球AI系統 v3.3", page_icon="☯️", layout="wide")
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

    st.title("梅花易數足球AI自主推理系統 v3.3")
    st.caption("分時段卦象＋客觀足球先驗＋勝平負平衡候選池＋結構化AI證據融合＋賽後校準閉環。")

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
